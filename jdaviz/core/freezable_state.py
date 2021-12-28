from glue.viewers.profile.state import ProfileViewerState
from glue_jupyter.bqplot.image.state import BqplotImageViewerState


class FreezableState():
    _frozen_state = []

    def __setattr__(self, k, v):
        if k[0] == '_' or k not in self._frozen_state:
            super().__setattr__(k, v)
        elif getattr(self, k) is None:
            # still allow Nones to be updated to initial values
            super().__setattr__(k, v)


class FreezableProfileViewerState(ProfileViewerState, FreezableState):
    pass


class FreezableBqplotImageViewerState(BqplotImageViewerState, FreezableState):
    pass
