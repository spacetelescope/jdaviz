from echo import delay_callback
import numpy as np

from glue.viewers.profile.state import ProfileViewerState
from glue_jupyter.bqplot.image.state import BqplotImageViewerState
from glue.viewers.matplotlib.state import DeferredDrawCallbackProperty as DDCProperty

__all__ = ['FreezableState', 'FreezableProfileViewerState', 'FreezableBqplotImageViewerState']


class FreezableState():
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

        with delay_callback(self, 'x_min', 'x_max'):
            self.x_min = x_min
            self.x_max = x_max


class FreezableBqplotImageViewerState(BqplotImageViewerState, FreezableState):
    linked_by_wcs = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def reset_limits(self, *event):
        if self.linked_by_wcs:
            x_min, x_max = np.inf, -np.inf
            y_min, y_max = np.inf, -np.inf

            for layer in self.layers:
                if not layer.visible:
                    continue
                data = next((x for x in self.data_collection if x.label == layer.layer.data.label))
                bounds = data.coords.pixel_bounds

                world_bottom_left = data.coords.pixel_to_world(0, 0)
                world_top_right = data.coords.pixel_to_world(bounds[0][1], bounds[1][1])

                pixel_bottom_left = self.reference_data.coords.world_to_pixel(world_bottom_left)
                pixel_top_right = self.reference_data.coords.world_to_pixel(world_top_right)

                x_min = min(x_min, pixel_bottom_left[0])
                x_max = max(x_max, pixel_top_right[0])
                y_min = min(y_min, pixel_bottom_left[1])
                y_max = max(y_max, pixel_top_right[1])
        else:
            x_min, x_max = -0.5, -np.inf
            y_min, y_max = -0.5, -np.inf
            for layer in self.layers:
                if not layer.visible:
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
