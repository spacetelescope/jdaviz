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
    pass
