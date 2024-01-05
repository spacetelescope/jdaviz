from contextlib import contextmanager
from echo import delay_callback, CallbackProperty
import numpy as np

from glue.viewers.profile.state import ProfileViewerState
from glue_jupyter.bqplot.image.state import BqplotImageViewerState
from glue.viewers.matplotlib.state import DeferredDrawCallbackProperty as DDCProperty

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

    zoom_level = CallbackProperty(1.0, docstring='Zoom-level')
    zoom_center = CallbackProperty((0.0, 0.0), docstring='Coordinates of center of zoom box')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.wcs_only_layers = []  # For Imviz rotation use.
        self._during_zoom_sync = False
        self.add_callback('zoom_level', self._set_zoom_level)
        self.add_callback('zoom_center', self._set_zoom_center)
        for attr in ('x_min', 'x_max', 'y_min', 'y_max'):
            self.add_callback(attr, self._set_axes_lim)

    @contextmanager
    def during_zoom_sync(self):
        self._during_zoom_sync = True
        try:
            yield
        except Exception:
            self._during_zoom_sync = False
            raise
        self._during_zoom_sync = False

    def _set_zoom_level(self, zoom_level):
        if self._during_zoom_sync or not hasattr(self, '_viewer') or self._viewer.shape is None:
            return
        if zoom_level <= 0.0:
            raise ValueError("zoom_level must be positive")

        cur_xcen = (self.x_min + self.x_max) * 0.5
        new_dx = self._viewer.shape[1] * 0.5 / zoom_level
        new_x_min = cur_xcen - new_dx
        new_x_max = cur_xcen + new_dx

        with self.during_zoom_sync():
            self.x_min = new_x_min - 0.5
            self.x_max = new_x_max - 0.5

            # We need to adjust the limits in here to avoid triggering all
            # the update events then changing the limits again.
            self._adjust_limits_aspect()

    def _set_zoom_center(self, zoom_center):
        if self._during_zoom_sync:
            return

        cur_xcen = (self.x_min + self.x_max) * 0.5
        cur_ycen = (self.y_min + self.y_max) * 0.5
        delta_x = zoom_center[0] - cur_xcen
        delta_y = zoom_center[1] - cur_ycen

        with self.during_zoom_sync():
            self.x_min += delta_x
            self.x_max += delta_x
            self.y_min += delta_y
            self.y_max += delta_y

    def _set_axes_lim(self, *args):
        if self._during_zoom_sync or not hasattr(self, '_viewer') or self._viewer.shape is None:
            return

        screenx = self._viewer.shape[1]
        screeny = self._viewer.shape[0]
        zoom_x = screenx / (self.x_max - self.x_min)
        zoom_y = screeny / (self.y_max - self.y_min)
        center_x = 0.5 * (self.x_max + self.x_min)
        center_y = 0.5 * (self.y_max + self.y_min)

        with self.during_zoom_sync():
            self.zoom_level = max(zoom_x, zoom_y)  # Similar to Ginga get_scale()
            self.zoom_center = (center_x, center_y)

    def reset_limits(self, *event):
        if self.reference_data is None:  # Nothing to do
            return

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

                x_max = max(x_max, layer.layer.data[pixel_ids[1]].max() + 0.5)
                y_max = max(y_max, layer.layer.data[pixel_ids[0]].max() + 0.5)

        with delay_callback(self, 'x_min', 'x_max', 'y_min', 'y_max'):
            self.x_min = x_min
            self.x_max = x_max
            self.y_min = y_min
            self.y_max = y_max
            # We need to adjust the limits in here to avoid triggering all
            # the update events then changing the limits again.
            self._adjust_limits_aspect()
