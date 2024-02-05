from contextlib import contextmanager
from echo import delay_callback, CallbackProperty
import numpy as np

from glue.viewers.profile.state import ProfileViewerState
from glue_jupyter.bqplot.image.state import BqplotImageViewerState
from glue.viewers.matplotlib.state import DeferredDrawCallbackProperty as DDCProperty

from jdaviz.configs.imviz.helper import get_reference_image_data

__all__ = ['FreezableState', 'FreezableProfileViewerState', 'FreezableBqplotImageViewerState']


class FreezableState:
    _frozen_state = []

    def __setattr__(self, k, v):
        if k[0] == '_' or k not in self._frozen_state:
            super().__setattr__(k, v)
        elif getattr(self, k) is None:
            # still allow Nones to be updated to initial values
            super().__setattr__(k, v)


class FreezableProfileViewerState(ProfileViewerState, FreezableState):
    show_uncertainty = DDCProperty(False, docstring='Whether to show data uncertainties')

    def _reset_x_limits(self, *event):
        # override glue's _reset_x_limits to account for all layers,
        # not just reference data (_reset_y_limits already does so)
        # This is essentially copied directly from Glue's
        # ProfileViewerState._reset_y_limits but modified for x-limits
        if self.reference_data is None or self.x_att_pixel is None:
            return

        x_min, x_max = np.inf, -np.inf
        for layer in self.layers:
            try:
                profile = layer.profile
            except Exception:  # nosec
                # e.g. incompatible subset
                continue
            if profile is not None:
                x, y = profile
                if len(x) > 0:
                    x_min = min(x_min, np.nanmin(x))
                    x_max = max(x_max, np.nanmax(x))

        if not np.all(np.isfinite([x_min, x_max])):
            return

        with delay_callback(self, 'x_min', 'x_max'):
            self.x_min = x_min
            self.x_max = x_max


class FreezableBqplotImageViewerState(BqplotImageViewerState, FreezableState):
    linked_by_wcs = False

    zoom_radius = CallbackProperty(1.0, docstring="Zoom radius")
    zoom_center_x = CallbackProperty(0.0, docstring='x-coordinate of center of zoom box')
    zoom_center_y = CallbackProperty(0.0, docstring='y-coordinate of center of zoom box')

    def __init__(self, *args, **kwargs):
        self.wcs_only_layers = []  # For Imviz rotation use.
        self._during_zoom_sync = False
        self.add_callback('zoom_radius', self._set_zoom_radius_center)
        self.add_callback('zoom_center_x', self._set_zoom_radius_center)
        self.add_callback('zoom_center_y', self._set_zoom_radius_center)
        for attr in ('x_min', 'x_max', 'y_min', 'y_max'):
            self.add_callback(attr, self._set_axes_lim)
        super().__init__(*args, **kwargs)

    @contextmanager
    def during_zoom_sync(self):
        self._during_zoom_sync = True
        try:
            yield
        except Exception:
            self._during_zoom_sync = False
            raise
        self._during_zoom_sync = False

    def _set_zoom_radius_center(self, *args):
        if self._during_zoom_sync or not hasattr(self, '_viewer') or self._viewer.shape is None:
            return

        # When WCS-linked (displayed on the sky): zoom_center_x/y and zoom_radius are in sky units,
        # x/y_min/max are in pixels of the WCS-only layer
        if self.linked_by_wcs:
            image, i_ref = get_reference_image_data(self._viewer.jdaviz_app, self._viewer.reference)
            ref_wcs = image.coords
            cr = ref_wcs.world_to_pixel_values((self.zoom_center_x, self.zoom_center_x+abs(self.zoom_radius)),  # noqa
                                               (self.zoom_center_y, self.zoom_center_y))
            center_x, center_xr = cr[0]
            center_y, _ = cr[1]
            radius = abs(center_xr - center_x)
        else:
            center_x, center_y = self.zoom_center_x, self.zoom_center_y
            radius = abs(self.zoom_radius)
        # now center_x/y and radius are in pixel units of the reference data, so can be used to
        # update limits

        with self.during_zoom_sync():
            x_min = center_x - radius
            x_max = center_x + radius
            y_min = center_y - radius
            y_max = center_y + radius
            self.x_min, self.x_max, self.y_min, self.y_max = x_min, x_max, y_min, y_max

            self._adjust_limits_aspect()

    def _set_axes_aspect_ratio(self, axes_ratio):
        # when aspect-ratio is changed (changing viewer.shape), ensure zoom/center are synced
        # with zoom-limits
        super()._set_axes_aspect_ratio(axes_ratio)
        self._set_axes_lim()

    def _set_axes_lim(self, *args):
        if self._during_zoom_sync or not hasattr(self, '_viewer') or self._viewer.shape is None:
            return
        if None in (self.x_min, self.x_max, self.y_min, self.y_max):
            return

        # When WCS-linked (displayed on the sky): zoom_center_x/y and zoom_radius are in sky units,
        # x/y_min/max are in pixels of the WCS-only layer
        if self.linked_by_wcs:
            image, i_ref = get_reference_image_data(self._viewer.jdaviz_app, self._viewer.reference)
            ref_wcs = image.coords
            lims = ref_wcs.pixel_to_world_values((self.x_min, self.x_max), (self.y_min, self.y_max))
            x_min, x_max = lims[0]
            y_min, y_max = lims[1]
        else:
            x_min, y_min = self.x_min, self.y_min
            x_max, y_max = self.x_max, self.y_max
        # now x_min/max, y_min/max are in axes units (degrees if WCS-linked, pixels otherwise)

        with self.during_zoom_sync():
            self.zoom_radius = abs(0.5 * min(x_max - x_min, y_max - y_min))
            self.zoom_center_x = 0.5 * (x_max + x_min)
            self.zoom_center_y = 0.5 * (y_max + y_min)

    def _get_reset_limits(self, return_as_world=False):
        wcs_success = False
        if self.linked_by_wcs and self.reference_data.coords is not None:
            x_min, x_max = np.inf, -np.inf
            y_min, y_max = np.inf, -np.inf

            for layer in self.layers:
                if not layer.visible:
                    continue

                data = next((x for x in self.data_collection if x.label == layer.layer.data.label))
                if data.coords is None:
                    # if no layers have coords, then wcs_success will remain
                    # false and limits will fallback based on pixel limit
                    continue

                pixel_ids = layer.layer.pixel_component_ids
                world_bottom_left = data.coords.pixel_to_world(0, 0)
                world_top_right = data.coords.pixel_to_world(layer.layer.data[pixel_ids[1]].max(),
                                                             layer.layer.data[pixel_ids[0]].max())

                if return_as_world:
                    x_min = min(x_min, world_bottom_left.ra.value)
                    x_max = max(x_max, world_top_right.ra.value)
                    y_min = min(y_min, world_bottom_left.dec.value)
                    y_max = max(y_max, world_top_right.dec.value)
                else:
                    pixel_bottom_left = self.reference_data.coords.world_to_pixel(world_bottom_left)
                    pixel_top_right = self.reference_data.coords.world_to_pixel(world_top_right)

                    x_min = min(x_min, pixel_bottom_left[0] - 0.5)
                    x_max = max(x_max, pixel_top_right[0] + 0.5)
                    y_min = min(y_min, pixel_bottom_left[1] - 0.5)
                    y_max = max(y_max, pixel_top_right[1] + 0.5)
                wcs_success = True

        if not wcs_success:
            x_min, x_max = -0.5, -np.inf
            y_min, y_max = -0.5, -np.inf
            for layer in self.layers:
                if not layer.visible or layer.layer.data.ndim == 1:
                    continue
                pixel_ids = layer.layer.pixel_component_ids
                pixel_id_x = [comp for comp in pixel_ids if comp.label.endswith('[x]')][0]
                pixel_id_y = [comp for comp in pixel_ids if comp.label.endswith('[y]')][0]

                x_max = max(x_max, layer.layer.data[pixel_id_x].max() + 0.5)
                y_max = max(y_max, layer.layer.data[pixel_id_y].max() + 0.5)

        return x_min, x_max, y_min, y_max

    def reset_limits(self, *event):
        # TODO: use consistent logic for all image viewers by removing this if-statement
        # if/when WCS linking is supported (i.e. in cubeviz)
        if getattr(self, '_viewer', None) is not None and self._viewer.jdaviz_app.config != 'imviz':
            return super().reset_limits(*event)
        if self.reference_data is None:  # Nothing to do
            return

        x_min, x_max, y_min, y_max = self._get_reset_limits()

        with delay_callback(self, 'x_min', 'x_max', 'y_min', 'y_max'):
            self.x_min, self.x_max, self.y_min, self.y_max = x_min, x_max, y_min, y_max
            # We need to adjust the limits in here to avoid triggering all
            # the update events then changing the limits again.
            self._adjust_limits_aspect()
