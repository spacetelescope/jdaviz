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


class FreezableBqplotImageViewerState(BqplotImageViewerState, FreezableState):
    pass
