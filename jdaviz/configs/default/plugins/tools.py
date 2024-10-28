from glue_jupyter.bqplot.profile import BqplotProfileView

from jdaviz.core.tools import SinglePixelRegion
from jdaviz.core.marks import PluginLine

__all__ = ['ProfileFromCube']


class ProfileFromCube(SinglePixelRegion):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._profile_viewer = None
        self._previous_bounds = None
        self._mark = None
        self._data = None

    def _reset_profile_viewer_bounds(self):
        self._profile_viewer.set_limits(
            y_min=self._previous_bounds[2], y_max=self._previous_bounds[3])

    def activate(self):
        self.viewer.add_event_callback(self.on_mouse_move, events=['mousemove', 'mouseleave'])
        if self._profile_viewer is None:
            # Get first profile viewer
            for _, viewer in self.viewer.jdaviz_helper.app._viewer_store.items():
                if isinstance(viewer, BqplotProfileView):
                    self._profile_viewer = viewer
                    break
        if self._mark is None:
            self._mark = PluginLine(self._profile_viewer, visible=False)
            self._profile_viewer.figure.marks = self._profile_viewer.figure.marks + [self._mark, ]
        # Store these so we can revert to previous user-set zoom after preview view
        self._previous_bounds = self._profile_viewer.get_limits()
        super().activate()

    def deactivate(self):
        self.viewer.remove_event_callback(self.on_mouse_move)
        self._reset_profile_viewer_bounds()
        super().deactivate()

    def on_mouse_move(self, data):
        raise NotImplementedError("must be implemented by subclasses")
