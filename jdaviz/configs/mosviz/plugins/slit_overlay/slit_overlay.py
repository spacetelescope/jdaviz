
from jdaviz.core.registries import tray_registry
from jdaviz.core.template_mixin import TemplateMixin
from jdaviz.utils import load_template
from jdaviz.core.events import SnackbarMessage

import numpy as np
from regions import RectangleSkyRegion, RectanglePixelRegion
from astropy.coordinates import Angle, SkyCoord
from astropy import units as u
from astropy.wcs import WCS

import bqplot

@tray_registry('g-slit-overlay', label="Slit Overlay")
class SlitOverlay(TemplateMixin):
    template = load_template("slit_overlay.vue", __file__).tag(sync=True)


    def jwst_header_to_skyregion(self, header):
        s_region = header['S_REGION']
        footprint = s_region.split("POLYGON ICRS")[1].split()
        ra = np.array(footprint[::2], dtype=np.float)
        dec = np.array(footprint[1::2], dtype=np.float)

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


    def vue_slit_overlay(self, *args, **kwargs):
        """
        Find slit information in 2D Spectrum metadata, find the correct
        wcs information from the image metadata, then plot the slit over the
        image viewer using both.
        """
        image_data = self.app.get_viewer("image-viewer").data()
        spec2d_data = self.app.get_viewer("spectrum-2d-viewer").data()

        if 'S_REGION' in spec2d_data[0].meta:
            header = spec2d_data[0].meta
            sky_region = self.jwst_header_to_skyregion(header)


            # Use wcs of image viewer to scale slit dimensions correctly
            wcs_image = WCS(image_data[0].meta)
            pixel_region = sky_region.to_pixel(wcs_image)


            # Create polygon region from the pixel region and set vertices
            pix_rec = pixel_region.to_polygon()

            x_coords = pix_rec.vertices.x
            y_coords = pix_rec.vertices.y

            fig_image = self.app.get_viewer("image-viewer").figure

            # Create LinearScale that is the same size as the image viewer
            scales = {'x': fig_image.interaction.x_scale, 'y': fig_image.interaction.y_scale}

            # Create slit
            patch2 = bqplot.Lines(x=x_coords, y=y_coords, scales=scales, fill='none', colors=["red"], stroke_width=2,
                                  close_path=True)

            # Visualize slit on the figure
            fig_image.marks = fig_image.marks + [patch2]

            snackbar_message = SnackbarMessage(
                "Slit successfully added to image viewer",
                color="success",
                sender=self)

        else:
            snackbar_message = SnackbarMessage(
                "\'S_REGION\' not found in Spectrum 2D meta attribute",
                color="error",
                sender=self)

        self.hub.broadcast(snackbar_message)

    def vue_slit_overlay_remove(self, *args, **kwargs):
        image_figure = self.app.get_viewer("image-viewer").figure
        image_figure.marks = [image_figure.marks[0]]
