import astropy.units as u
from astropy.coordinates import SkyCoord, Angle
from astropy.wcs import WCS
from gwcs.wcs import WCS as GWCS

from jdaviz.utils import data_has_valid_wcs, get_top_layer_index


class AID:
    """
    Common API methods for image viewers in astronomy, called
    the Astro Image Display API (AIDA)[1]_.

    References
    ----------
    .. [1] https://github.com/astropy/astro-image-display-api/

    """

    def __init__(self, viewer):
        self.viewer = viewer
        self.app = viewer.jdaviz_app

    def _get_image_glue_data(self, image_label):
        if image_label is None:
            i_top = get_top_layer_index(self.viewer)
            image = self.viewer.layers[i_top].layer

        else:
            for lyr in self.viewer.layers:
                image = lyr.layer
                if image.label == image_label:
                    break
            else:
                raise ValueError(f"No data with data_label {image_label}` found in viewer.")

        return image, image.label

    def set_viewport(self, center=None, fov=None, image_label=None, **kwargs):
        """
        Parameters
        ----------
        center : `~astropy.coordinates.SkyCoord` or tuple of floats
            Center the viewer on this coordinate.

        fov : `~astropy.units.Quantity` or tuple of floats
            Set the width of the viewport to span `field_of_view`.

        image_label : str
            Set the viewport with respect to the image
            with the data label: ``image_label``.
        """
        image, image_label = self._get_image_glue_data(image_label)

        if center is None:
            # get the current center in the pixel coords on reference data
            x_min, x_max, y_min, y_max = self.viewer.get_limits()
            center_x = 0.5 * (x_min + x_max)
            center_y = 0.5 * (y_min + y_max)
            center = (center_x, center_y)

        if isinstance(center, SkyCoord):
            reference_wcs = self.viewer.state.reference_data.coords

            if isinstance(reference_wcs, GWCS):
                reference_wcs = WCS(reference_wcs.to_fits_sip())

            reference_center_pix = reference_wcs.world_to_pixel(center)

        elif hasattr(center, '__len__') and isinstance(center[0], (float, int)):
            reference_center_pix = center

        current_width = self.viewer.state.x_max - self.viewer.state.x_min
        current_height = self.viewer.state.y_max - self.viewer.state.y_min

        if fov is None:
            new_width = current_width
            new_height = current_height
        else:
            if isinstance(fov, (u.Quantity, Angle)):
                current_fov = self._get_current_fov('sky')
                scale_factor = float(fov / current_fov)

            elif isinstance(fov, (float, int)):
                current_fov = self._get_current_fov('pixel')
                scale_factor = float(fov / current_fov)

            new_width = current_width * scale_factor
            new_height = current_height * scale_factor

        new_xmin = reference_center_pix[0] - (new_width * 0.5)
        new_ymin = reference_center_pix[1] - (new_height * 0.5)

        self.viewer.set_limits(
            x_min=new_xmin,
            x_max=new_xmin + new_width,
            y_min=new_ymin,
            y_max=new_ymin + new_height
        )

    def _get_current_fov(self, sky_or_pixel):
        x_min, x_max, y_min, y_max = self.viewer.get_limits()

        if sky_or_pixel == 'sky':
            wcs = self.viewer.state.reference_data.coords

            # for now, convert GWCS to FITS SIP so pixel to world
            # transformations can be done outside of the bounding box
            if isinstance(wcs, GWCS):
                wcs = WCS(wcs.to_fits_sip())

            lower_left, lower_right, upper_left = wcs.pixel_to_world(
                [x_min, y_min, x_min], [x_max, y_min, y_max]
            )

            return lower_left.separation(lower_right)
        else:
            return x_max - x_min

    def get_viewport(self, sky_or_pixel=None, image_label=None, **kwargs):
        """
        sky_or_pixel : str, optional
            If 'sky', the center will be returned as a `SkyCoord` object.
            If 'pixel', the center will be returned as a tuple of pixel coordinates.
            If `None`, the default behavior is to return the center as a `SkyCoord` if
            possible, or as a tuple of floats if the image is in pixel coordinates and has
            no WCS information.

        image_label : str, optional
            The label of the image to get the viewport for. If not given and there is only one
            image loaded, the viewport for that image is returned. If there are multiple images
            and no label is provided, an error is raised.

        Returns
        -------
        dict
            A dictionary containing the current viewport settings.
            The keys are 'center', 'fov', and 'image_label'.
            - 'center' is an `astropy.coordinates.SkyCoord` object or a tuple of floats.
            - 'fov' is an `astropy.units.Quantity` object or a float.
            - 'image_label' is a string representing the label of the image.
        """
        # viewer_aligned_by_wcs = self.app._align_by == 'wcs'

        image, image_label = self._get_image_glue_data(image_label)
        reference_data = self.viewer.state.reference_data
        reference_wcs = reference_data.coords

        x_min, x_max, y_min, y_max = self.viewer.get_limits()
        center_x = 0.5 * (x_min + x_max)
        center_y = 0.5 * (y_min + y_max)

        # default to 'sky' if sky/pixel not specified and WCS is available:
        if sky_or_pixel is None and data_has_valid_wcs(image):
            sky_or_pixel = 'sky'

        # if the image data have WCS, get the center sky coordinate:
        if sky_or_pixel == 'sky':
            if self.app._align_by == 'wcs':
                center = self.viewer._get_center_skycoord()
            else:
                center = reference_wcs.pixel_to_world(center_x, center_y)

            fov = self._get_current_fov(sky_or_pixel)

        else:
            center = (center_x, center_y)
            fov = x_max - x_min

        return dict(center=center, fov=fov, image_label=image_label)
