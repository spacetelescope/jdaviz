from echo import delay_callback, ignore_callback
import numpy as np
import astropy.units as u
from astropy.coordinates import SkyCoord, Angle
from astropy.wcs import WCS
from gwcs.wcs import WCS as GWCS

from jdaviz.utils import get_top_layer_index
from jdaviz.configs.imviz.wcs_utils import get_compass_info


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

    def _set_center(self, center):
        if center is None:
            return

        imviz_aligned_by_wcs = self.app._align_by == 'wcs'
        if isinstance(center, SkyCoord):
            if imviz_aligned_by_wcs:
                center = center.ra.degree, center.dec.degree
            else:
                reference_wcs = self.viewer.state.reference_data.coords

                if isinstance(reference_wcs, GWCS):
                    reference_wcs = WCS(reference_wcs.to_fits_sip())

                center = reference_wcs.world_to_pixel(center)

        elif not hasattr(center, '__len__') or not isinstance(center[0], (float, int)):
            raise ValueError(
                "The AID API supports `center` arguments as SkyCoords or as "
                f"a tuple of floats in pixel coordinates, got {center=}."
            )

        with delay_callback(self.viewer.state, "zoom_center_y", "zoom_center_x"):
            (
                self.viewer.state.zoom_center_x,
                self.viewer.state.zoom_center_y
            ) = center

    def _set_fov(self, fov):
        if fov is None:
            return

        if isinstance(fov, (u.Quantity, Angle)):
            current_fov = self._get_current_fov('sky')
        elif isinstance(fov, (float, int)):
            current_fov = self._get_current_fov('pixel')
        else:
            raise ValueError(
                f"`fov` must be a Quantity or tuple of floats, got {fov=}"
            )

        scale_factor = float(fov / current_fov)

        with delay_callback(self.viewer.state, "zoom_radius"):
            self.viewer.state.zoom_radius = self.viewer.state.zoom_radius * scale_factor

    def _set_rotation(self, rotation):
        if rotation is None:
            return

        orientation = self.app._jdaviz_helper.plugins.get('Orientation', None)

        if orientation.align_by != 'WCS':
            raise ValueError("The viewer must be aligned by WCS to use `set_rotation`.")

        if isinstance(rotation, (u.Quantity, Angle)):
            rotation = rotation.to_value(u.deg)
        elif not isinstance(rotation, (float, int)):
            raise ValueError(
                f"`rotation` must be a Quantity or float, got {rotation=}"
            )

        degn = orientation._obj._get_wcs_angles()[-3]
        rotation_angle = (degn + rotation) % 360

        label = f'{rotation:.2f} deg east of north'

        if label == orientation._obj.orientation.selected:
            return
        elif label in orientation._obj.orientation.choices:
            orientation._obj.orientation.selected = label
        else:
            orientation._obj.orientation.selected = "Default orientation"
            orientation.add_orientation(
                east_left=True,
                set_on_create=True,
                label=label,
                rotation_angle=rotation_angle
            )

    def set_viewport(self, center=None, fov=None, rotation=None, image_label=None, **kwargs):
        """
        Parameters
        ----------
        center : `~astropy.coordinates.SkyCoord` or tuple of floats
            Center the viewer on this coordinate.

        fov : `~astropy.units.Quantity` or tuple of floats
            Set the width of the viewport to span `field_of_view`.

            Set the viewport with respect to the image
            with the data label: ``image_label``.
        """
        with ignore_callback(
            self.viewer.state,
            'x_min', 'x_max', 'y_min', 'y_max',
            'zoom_center_x', 'zoom_center_y', 'zoom_radius'
        ):
            self._set_rotation(rotation)

        self._set_center(center)
        self._set_fov(fov)

    def _mean_pixel_scale(self, data):
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

    def _get_current_fov(self, sky_or_pixel=None):
        state = self.viewer.state
        wcs = state.reference_data.coords

        pixel_fov = min(
            state.x_max - state.x_min,
            state.y_max - state.y_min
        )

        if sky_or_pixel == 'pixel':
            return pixel_fov
        if not any(c.strip() for c in wcs.wcs.ctype):
            raise ValueError("The image must have valid WCS to return `fov` in `sky`.")

        if isinstance(wcs, GWCS):
            wcs = WCS(wcs.to_fits_sip())

        # compute the mean of the height and width of the
        # viewer's FOV on ``data`` in world units:
        x_corners = [
            state.x_min,
            state.x_max,
            state.x_min
        ]
        y_corners = [
            state.y_min,
            state.y_min,
            state.y_max
        ]

        sky_corners = wcs.pixel_to_world(x_corners, y_corners)
        height_sky = sky_corners[0].separation(sky_corners[2])
        width_sky = sky_corners[0].separation(sky_corners[1])

        current_fov = min([width_sky, height_sky])

        return current_fov

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
        if sky_or_pixel in ('sky', None):
            if self.app._align_by == 'wcs':
                center = self.viewer._get_center_skycoord()
            else:
                center = reference_wcs.pixel_to_world(center_x, center_y)
        else:
            center = (center_x, center_y)

        return center

    def _get_current_rotation(self):
        reference_data = self.viewer.state.reference_data
        degn = get_compass_info(
            reference_data.coords, reference_data.shape
        )[-3]
        rotation = Angle(-degn, unit=u.deg).wrap_at(360*u.deg)

        return rotation

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
            fov=self._get_current_fov(sky_or_pixel=sky_or_pixel),
            rotation=self._get_current_rotation(),
            image_label=image_label
        )
