import time
import os

from glue.config import viewer_tool
from glue.viewers.common.tool import CheckableTool

from jdaviz.core.events import SliceSelectWavelengthMessage, SliceToolStateMessage

__all__ = ['SelectSlice']

ICON_DIR = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'data', 'icons')


@viewer_tool
class SelectSlice(CheckableTool):
    icon = os.path.join(ICON_DIR, 'slice.svg')
    tool_id = 'jdaviz:selectslice'
    action_text = 'Select cube slice (spectral axis)'
    tool_tip = 'Select cube slice (spectral axis)'

    def __init__(self, viewer, **kwargs):
        self._time_last = 0
        super().__init__(viewer, **kwargs)

    def activate(self):
        self.viewer.add_event_callback(self.on_mouse_event,
                                       events=['dragmove', 'click'])
        msg = SliceToolStateMessage({'active': True}, sender=self)
        self.viewer.session.hub.broadcast(msg)

    def deactivate(self):
        self.viewer.remove_event_callback(self.on_mouse_event)
        msg = SliceToolStateMessage({'active': False}, sender=self)
        self.viewer.session.hub.broadcast(msg)

    def on_mouse_event(self, data):
        if (time.time() - self._time_last) <= 0.2:
            # throttle to 200ms
            return

        msg = SliceSelectWavelengthMessage(wavelength=data['domain']['x'], sender=self)
        self.viewer.session.hub.broadcast(msg)

        self._time_last = time.time()
