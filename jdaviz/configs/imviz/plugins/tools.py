from echo import delay_callback
from glue.config import viewer_tool
from glue_jupyter.bqplot.common.tools import InteractCheckableTool

__all__ = []


@viewer_tool
class BqplotMatchWCS(InteractCheckableTool):

    icon = 'glue_link'
    tool_id = 'bqplot:matchwcs'
    action_text = 'Match WCS between images'
    tool_tip = 'Click on image to have the other image viewer show the same coordinates'

    def __init__(self, viewer, **kwargs):

        super().__init__(viewer, **kwargs)

    def activate(self):
        self.viewer.add_event_callback(self.on_mouse_or_key_event, events=['click'])

    def deactivate(self):
        self.viewer.remove_event_callback(self.on_mouse_or_key_event)

    def on_mouse_or_key_event(self, data):
        if data['event'] == 'click':
            x = data['domain']['x']
            y = data['domain']['y']
            dx = self.viewer.state.x_max - self.viewer.state.x_min
            dy = self.viewer.state.y_max - self.viewer.state.y_min
            for viewer in self.viewer.session.application.viewers:
                with delay_callback(viewer.state, 'x_min', 'x_max', 'y_min', 'y_max'):
                    viewer.state.x_min = x - dx / 2
                    viewer.state.x_max = x + dx / 2
                    viewer.state.y_min = y - dy / 2
                    viewer.state.y_max = y + dy / 2
