import bqplot
import numpy as np
from astropy import units as u
from astropy.coordinates import Angle, SkyCoord
from regions import PolygonSkyRegion
from traitlets import Bool

from jdaviz.core.events import SnackbarMessage
from jdaviz.core.registries import tray_registry
from jdaviz.core.template_mixin import PluginTemplateMixin

__all__ = ['SlitOverlay', 'jwst_header_to_skyregion']


def jwst_header_to_skyregion(header):
    """Convert S_REGION in given FITS header for JWST data into sky region."""
    s_region = header['S_REGION']
    footprint = s_region.split("POLYGON ICRS")[1].split()
    ra = np.array(footprint[::2], dtype=float)
    dec = np.array(footprint[1::2], dtype=float)
    corners = SkyCoord(ra, dec, unit="deg")
    skyregion = PolygonSkyRegion(corners)

    # Need these for zooming
    length = corners[0].separation(corners[1])
    width = corners[1].separation(corners[2])
    skyregion.height = Angle(max(length, width), u.deg)
    skyregion.center = SkyCoord(ra.mean(), dec.mean(), unit="deg")

    return skyregion


@tray_registry('g-slit-overlay', label="Slit Overlay",
               viewer_requirements=['table', 'image', 'spectrum-2d', 'spectrum'])
class SlitOverlay(PluginTemplateMixin):
    template_file = __file__, "slit_overlay.vue"
    visible = Bool(True).tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        table = self.app.get_viewer(self._default_table_viewer_reference_name)
        table.figure_widget.observe(self.place_slit_overlay, names=['highlighted'])

        self._slit_overlay_mark = None

    @property
    def _default_table_viewer_reference_name(self):
        return getattr(
            self.app._jdaviz_helper, '_default_table_viewer_reference_name', 'table-viewer'
        )

    @property
    def _default_image_viewer_reference_name(self):
        return getattr(
            self.app._jdaviz_helper, '_default_image_viewer_reference_name', 'image-viewer'
        )

    @property
    def _default_spectrum_viewer_reference_name(self):
        return getattr(
            self.app._jdaviz_helper, '_default_spectrum_viewer_reference_name', 'spectrum-viewer'
        )

    @property
    def _default_spectrum_2d_viewer_reference_name(self):
        return getattr(
            self.app._jdaviz_helper,
            '_default_spectrum_2d_viewer_reference_name',
            'spectrum-2d-viewer'
        )

    def vue_change_visible(self, *args, **kwargs):
        if self.visible:
            self.place_slit_overlay()
        else:
            self.remove_slit_overlay()

    def place_slit_overlay(self, *args, **kwargs):
        """
        Find slit information in 2D Spectrum metadata, find the correct
        wcs information from the image metadata, then plot the slit over the
        image viewer using both.
        """
        if not self.visible:
            return

        snackbar_message = None

        # Clear existing slits on the image viewer
        self.remove_slit_overlay()

        # Get data from relevant viewers
        image_data = self.app.get_viewer(
            self._default_image_viewer_reference_name
        ).state.reference_data
        spec2d_data = self.app.get_viewer(
            self._default_spectrum_2d_viewer_reference_name
        ).data()

        # 'S_REGION' contains slit information. Bypass in case no images exist.
        if image_data is not None:
            # Only use S_REGION for Nirspec data, turn the plugin off
            # if other data is loaded
            if (len(spec2d_data) > 0 and 'S_REGION' in spec2d_data[0].meta
                    and spec2d_data[0].meta.get('INSTRUME', '').lower() == "nirspec"):
                header = spec2d_data[0].meta
                sky_region = jwst_header_to_skyregion(header)

                # Use wcs of image viewer to scale slit dimensions correctly
                pix_rec = sky_region.to_pixel(image_data.coords)

                x_coords = pix_rec.vertices.x
                y_coords = pix_rec.vertices.y

                image_viewer = self.app.get_viewer(self._default_image_viewer_reference_name)
                fig_image = image_viewer.figure

                if image_viewer.toolbar.active_tool is not None:
                    image_viewer.toolbar.active_tool = None

                # Create LinearScale that is the same size as the image viewer
                scales = {'x': fig_image.interaction.x_scale, 'y': fig_image.interaction.y_scale}

                # Create slit
                patch2 = bqplot.Lines(x=x_coords, y=y_coords, scales=scales,
                                      fill='none', colors=["red"], stroke_width=2,
                                      close_path=True)

                # Visualize slit on the figure
                fig_image.marks = fig_image.marks + [patch2]

                self._slit_overlay_mark = patch2

            else:
                self.visible = False
                snackbar_message = SnackbarMessage(
                    "\'S_REGION\' not found in Spectrum 2D meta attribute, "
                    "turning slit overlay off",
                    color="warning",
                    sender=self)

        if snackbar_message:
            self.hub.broadcast(snackbar_message)

    def remove_slit_overlay(self):
        if self._slit_overlay_mark is not None:
            image_figure = self.app.get_viewer(
                self._default_image_viewer_reference_name
            ).figure
            # We need to do the following instead of just removing directly on
            # the marks otherwise traitlets doesn't register a change in the
            # marks.
            image_figure.marks.remove(self._slit_overlay_mark)
            image_figure.send_state('marks')
            self._slit_overlay_mark = None
