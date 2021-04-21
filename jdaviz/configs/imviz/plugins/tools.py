from echo import delay_callback
from glue.config import viewer_tool
from glue_jupyter.bqplot.common.tools import InteractCheckableTool, Tool
from glue.plugins.wcs_autolinking.wcs_autolinking import wcs_autolink, WCSLink

__all__ = []


@viewer_tool
class BlinkOnce(Tool):
    icon = 'glue_forward'
    tool_id = 'bqplot:blinkonce'
    action_text = 'Go to next image'
    tool_tip = ('Click on this button to display the next image, '
                'or you can also press the "b" key anytime')

    def __init__(self, viewer, **kwargs):
        super().__init__(viewer, **kwargs)

    def activate(self):
        self.viewer.blink_once()


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

        # For now clickling this will automatically set up links between datasets. We
        # do this when activating this tool so that this ends up being 'opt-in' only
        # when the user wants to match WCS.

        # Find all possible WCS links in the data collection
        wcs_links = wcs_autolink(self.viewer.session.data_collection)

        # Add only those links that don't already exist
        for link in wcs_links:
            exists = False
            for existing_link in self.viewer.session.data_collection.external_links:
                if isinstance(existing_link, WCSLink):
                    if (link.data1 is existing_link.data1
                            and link.data2 is existing_link.data2):
                        exists = True
                        break
            if not exists:
                self.viewer.session.data_collection.add_link(link)

        # Set the reference data in other viewers to be the same as the current viewer.
        # If adding the data to the viewer, make sure it is not actually shown since the
        # user didn't request it.
        for viewer in self.viewer.session.application.viewers:
            if viewer is not self.viewer:
                if self.viewer.state.reference_data not in viewer.state.layers_data:
                    viewer.add_data(self.viewer.state.reference_data)
                    for layer in viewer.state.layers:
                        if layer.layer is self.viewer.state.reference_data:
                            layer.visible = False
                            break
                viewer.state.reference_data = self.viewer.state.reference_data

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


@viewer_tool
class BqplotContrastBias(InteractCheckableTool):

    icon = 'glue_contrast'
    tool_id = 'bqplot:contrastbias'
    action_text = 'Adjust contrast/bias'
    tool_tip = 'Drag left/right for cut level range and up/down for center value'

    def __init__(self, viewer, **kwargs):
        super().__init__(viewer, **kwargs)
        self._reset()

    def _reset(self):
        self._prev_x = None
        self._prev_y = None

    def activate(self):
        # Other drag events: dragstart, dragend
        self.viewer.add_event_callback(self.on_mouse_or_key_event,
                                       events=['dragstart', 'dragmove', 'dragend'])

    def deactivate(self):
        self._reset()
        self.viewer.remove_event_callback(self.on_mouse_or_key_event)

    def on_mouse_or_key_event(self, data):
        event = data['event']
        if event == 'dragmove':
            cur_x = data['domain']['x']
            cur_y = data['domain']['y']
            # TODO:
            # 1. Decide whether moving up/down or left/right. What about diagonal?
            # 2a. up/down = Grab current cut center, translate delta movement to delta cut center, apply
            # 2b. left/right = Grab current cut level range, translate movement..., apply
            # 3. Profit!!!
            self._prev_x = cur_x
            self._prev_y = cur_y
        elif event == 'dragstart':
            self._prev_x = data['domain']['x']
            self._prev_y = data['domain']['y']
        elif event == 'dragend':
            self._reset()
