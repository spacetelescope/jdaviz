from echo import delay_callback

import numpy as np
import astropy.units as u
from astropy.coordinates import SkyCoord, Angle
from astropy.wcs import WCS
from gwcs.wcs import WCS as GWCS

from jdaviz.utils import get_top_layer_index


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
                raise ValueError(f"No data with data_label `{image_label}` found in viewer.")

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
        imviz_aligned_by_wcs = self.app._align_by == 'wcs'

        with delay_callback(
            self.viewer.state,
            'x_min', 'x_max', 'y_min', 'y_max',
            'zoom_center_x', 'zoom_center_y', 'zoom_radius'
        ):
            if center is not None:
                if isinstance(center, SkyCoord):
                    if imviz_aligned_by_wcs:
                        (
                            self.viewer.state.zoom_center_x,
                            self.viewer.state.zoom_center_y
                        ) = center.ra.degree, center.dec.degree
                    else:
                        reference_wcs = self.viewer.state.reference_data.coords

                        if isinstance(reference_wcs, GWCS):
                            reference_wcs = WCS(reference_wcs.to_fits_sip())

                        (
                            self.viewer.state.zoom_center_x,
                            self.viewer.state.zoom_center_y
                        ) = reference_wcs.world_to_pixel(center)

                elif hasattr(center, '__len__') and isinstance(center[0], (float, int)):
                    (
                        self.viewer.state.zoom_center_x,
                        self.viewer.state.zoom_center_y
                    ) = center
                else:
                    raise ValueError(
                        "The AID API supports `center` arguments as SkyCoords or as "
                        f"a tuple of floats in pixel coordinates, got {center=}."
                    )

            if fov is not None:
                if isinstance(fov, (u.Quantity, Angle)):
                    current_fov = self._get_current_fov('sky', image_label)
                    scale_factor = float(fov / current_fov)

                elif isinstance(fov, (float, int)):
                    current_fov = self._get_current_fov('pixel', image_label)
                    scale_factor = float(fov / current_fov)

                else:
                    raise ValueError(
                        f"`fov` must be a Quantity or tuple of floats, got {fov=}"
                    )

                self.viewer.state.zoom_radius = self.viewer.state.zoom_radius * scale_factor

    def _mean_pixel_scale(self, data):
        """get the mean of the x and y pixel scales from the low level wcs"""
        wcs = data.coords

        # for now, convert GWCS to FITS SIP so pixel to world
        # transformations can be done outside of the bounding box
        if isinstance(wcs, GWCS):
            wcs = WCS(wcs.to_fits_sip())

        abs_cdelts = u.Quantity([
            abs(cdelt) * u.Unit(cunit)
            for cdelt, cunit in zip(wcs.wcs.cdelt, wcs.wcs.cunit)
        ])
        return np.mean(abs_cdelts)

    def _get_current_fov(self, sky_or_pixel, image_label):
        imviz_aligned_by_wcs = self.app._align_by == 'wcs'

        # `zoom_radius` is the distance from the center of the viewer
        # to the nearest edge in units of pixels
        zoom_radius = self.viewer.state.zoom_radius

        # default to 'sky' if sky/pixel not specified and WCS is available:
        if sky_or_pixel in (None, 'sky'):
            if not imviz_aligned_by_wcs:
                ref_data, _ = self._get_image_glue_data(image_label)
                pixel_scale = self._mean_pixel_scale(ref_data)
                return pixel_scale * 2 * zoom_radius * u.deg
            else:
                return 2 * zoom_radius * u.deg

        return 2 * zoom_radius

    def _get_current_center(self, sky_or_pixel, image_label=None):
        # center pixel coordinates on the reference data:
        center_x = self.viewer.state.zoom_center_x
        center_y = self.viewer.state.zoom_center_y

        if self.app._align_by == 'wcs':
            reference_data = self.viewer.state.reference_data
        else:
            reference_data, image_label = self._get_image_glue_data(image_label)

        reference_wcs = reference_data.coords

        # # if the image data have WCS, get the center sky coordinate:
        if sky_or_pixel == 'sky':
            if self.app._align_by == 'wcs':
                center = self.viewer._get_center_skycoord()
            else:
                center = reference_wcs.pixel_to_world(center_x, center_y)
        else:
            center = (center_x, center_y)

        return center

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
        image, image_label = self._get_image_glue_data(image_label)

        return dict(
            center=self._get_current_center(sky_or_pixel=sky_or_pixel, image_label=image_label),
            fov=self._get_current_fov(sky_or_pixel=sky_or_pixel, image_label=image_label),
            image_label=image_label
        )
