import time
import os

from glue.config import viewer_tool
from glue.viewers.common.tool import CheckableTool
from glue.core.roi import RectangularROI
from glue.core.edit_subset_mode import NewMode

from jdaviz.core.events import SliceSelectWavelengthMessage, SliceToolStateMessage

__all__ = []


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


@viewer_tool
class SpectrumPerSpaxel(CheckableTool):

    icon = os.path.join(ICON_DIR, 'pixelspectra.svg')
    tool_id = 'jdaviz:spectrumperspaxel'
    action_text = 'See spectrum at a single spaxel'
    tool_tip = 'Click on the viewer and see the spectrum at that spaxel in the spectrum viewer'

    def __init__(self, viewer, **kwargs):
        super().__init__(viewer, **kwargs)

    def activate(self):
        self.viewer.add_event_callback(self.on_mouse_event,
                                       events=['click'])

    def deactivate(self):
        self.viewer.remove_event_callback(self.on_mouse_event)

    def on_mouse_event(self, data):
        event = data['event']

        if event == 'click' and data['altKey'] is True:
            self.alt_subset_at_spaxel(data)
        elif event == 'click':
            self.subset_at_spaxel(data)

    def alt_subset_at_spaxel(self, data):
        # Add a new subset if the alt key is held down
        previous_subset_mode = self.viewer.session.edit_subset_mode.mode

        self.viewer.session.edit_subset_mode.mode = NewMode
        self.subset_at_spaxel(data)
        self.viewer.session.edit_subset_mode.mode = previous_subset_mode

    def subset_at_spaxel(self, data):
        x = data['domain']['x']
        y = data['domain']['y']
        xmin, xmax, ymin, ymax = self._calc_coords(x, y)
        self.viewer.apply_roi(RectangularROI(xmin, xmax, ymin, ymax))

    def _calc_coords(self, x, y):
        xmin = x - 0.5
        xmax = x + 0.5
        ymin = y - 0.5
        ymax = y + 0.5

        return xmin, xmax, ymin, ymax
