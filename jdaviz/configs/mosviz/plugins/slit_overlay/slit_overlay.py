from jdaviz.core.registries import tray_registry
from jdaviz.core.template_mixin import PluginTemplateMixin
from jdaviz.core.events import SnackbarMessage

from traitlets import Bool

import numpy as np
from regions import RectangleSkyRegion
from astropy.coordinates import Angle, SkyCoord
from astropy import units as u

import bqplot

__all__ = ['SlitOverlay', 'jwst_header_to_skyregion']


def jwst_header_to_skyregion(header):
    s_region = header['S_REGION']
    footprint = s_region.split("POLYGON ICRS")[1].split()
    ra = np.array(footprint[::2], dtype=float)
    dec = np.array(footprint[1::2], dtype=float)

    # Find center of slit
    cra = (max(ra) + min(ra)) / 2
    cdec = (max(dec) + min(dec)) / 2

    # Find center as skycoord
    skycoord = SkyCoord(cra, cdec,
                        unit=(u.Unit(u.deg),
                              u.Unit(u.deg)))

    # Puts corners of slit into skycoord object
    corners = SkyCoord(ra, dec, unit="deg")

    # Compute length and width
    length = corners[0].separation(corners[1])
    width = corners[1].separation(corners[2])
    length = Angle(length, u.deg)
    width = Angle(width, u.deg)

    skyregion = RectangleSkyRegion(center=skycoord, width=width, height=length)
    return skyregion


@tray_registry('g-slit-overlay', label="Slit Overlay",
               viewer_requirements=['table', 'image', 'spectrum-2d', 'spectrum'])
class SlitOverlay(PluginTemplateMixin):
    template_file = __file__, "slit_overlay.vue"
    visible = Bool(True).tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._default_table_viewer_reference_name = kwargs.get(
            "table_viewer_reference_name", "table-viewer"
        )
        self._default_image_viewer_reference_name = kwargs.get(
            "image_viewer_reference_name", "image-viewer"
        )
        self._default_spectrum_2d_viewer_reference_name = kwargs.get(
            "spectrum_2d_viewer_reference_name", "spectrum-2d-viewer"
        )
        self._default_spectrum_viewer_reference_name = kwargs.get(
            "spectrum_viewer_reference_name", "spectrum-viewer"
        )
        table = self.app.get_viewer(self._default_table_viewer_reference_name)
        table.figure_widget.observe(self.place_slit_overlay, names=['highlighted'])

        self._slit_overlay_mark = None

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
                pixel_region = sky_region.to_pixel(image_data.coords)

                # Create polygon region from the pixel region and set vertices
                pix_rec = pixel_region.to_polygon()

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
