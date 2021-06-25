import time
import os

from echo import delay_callback

from glue.config import viewer_tool
from glue_jupyter.bqplot.common.tools import Tool
from glue.viewers.common.tool import CheckableTool
from glue.plugins.wcs_autolinking.wcs_autolinking import wcs_autolink, WCSLink
from glue_jupyter.bqplot.common.tools import BqplotPanZoomMode

__all__ = []

ICON_DIR = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'data', 'icons')


@viewer_tool
class BlinkOnce(Tool):
    icon = 'glue_forward'
    tool_id = 'bqplot:blinkonce'
    action_text = 'Go to next image'
    tool_tip = ('Click on this button to display the next image, '
                'or you can also press the "b" key anytime')

    def activate(self):
        self.viewer.blink_once()


@viewer_tool
class BqplotMatchWCS(BqplotPanZoomMode):

    icon = os.path.join(ICON_DIR, 'pan_wcs.svg')
    tool_id = 'bqplot:panzoomwcs'
    action_text = 'Pan, matching WCS between viwers'
    tool_tip = 'Pan and Zoom in this viewer to see the same regions in other viewers'

    def activate(self):

        super().activate()

        self.viewer.state.add_callback('x_min', self.on_limits_change)
        self.viewer.state.add_callback('x_max', self.on_limits_change)
        self.viewer.state.add_callback('y_min', self.on_limits_change)
        self.viewer.state.add_callback('y_max', self.on_limits_change)

        # For now clicking this will automatically set up links between datasets. We
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

        # Trigger a sync so the initial limits match
        self.on_limits_change()

    def deactivate(self):

        self.viewer.state.remove_callback('x_min', self.on_limits_change)
        self.viewer.state.remove_callback('x_max', self.on_limits_change)
        self.viewer.state.remove_callback('y_min', self.on_limits_change)
        self.viewer.state.remove_callback('y_max', self.on_limits_change)

        super().deactivate()

    def on_limits_change(self, *args):
        for viewer in self.viewer.session.application.viewers:
            if viewer is not self.viewer:
                with delay_callback(viewer.state, 'x_min', 'x_max', 'y_min', 'y_max'):
                    viewer.state.x_min = self.viewer.state.x_min
                    viewer.state.x_max = self.viewer.state.x_max
                    viewer.state.y_min = self.viewer.state.y_min
                    viewer.state.y_max = self.viewer.state.y_max


@viewer_tool
class BqplotContrastBias(CheckableTool):

    icon = 'glue_contrast'
    tool_id = 'bqplot:contrastbias'
    action_text = 'Adjust contrast/bias'
    tool_tip = 'Click and drag to adjust, double-click to reset'

    def __init__(self, viewer, **kwargs):
        self._time_last = 0
        super().__init__(viewer, **kwargs)

    def activate(self):
        self.viewer.add_event_callback(self.on_mouse_or_key_event,
                                       events=['dragstart', 'dragmove',
                                               'dragend', 'dblclick'])

    def deactivate(self):
        self.viewer.remove_event_callback(self.on_mouse_or_key_event)

    def on_mouse_or_key_event(self, data):
        from jdaviz.configs.imviz.helper import get_top_layer_index

        event = data['event']

        # Note that we throttle this to 200ms here as changing the contrast
        # and bias it expensive since it forces the whole image to be redrawn
        if event == 'dragmove':
            if (time.time() - self._time_last) <= 0.2:
                return

            event_x = data['domain']['x']
            event_y = data['domain']['y']

            if ((event_x < self.viewer.state.x_min) or
                    (event_x >= self.viewer.state.x_max) or
                    (event_y < self.viewer.state.y_min) or
                    (event_y >= self.viewer.state.y_max)):
                return

            x = event_x / (self.viewer.state.x_max - self.viewer.state.x_min)
            y = event_y / (self.viewer.state.y_max - self.viewer.state.y_min)

            # When blinked, first layer might not be top layer
            i_top = get_top_layer_index(self.viewer)
            state = self.viewer.layers[i_top].state

            # https://github.com/glue-viz/glue/blob/master/glue/viewers/image/qt/contrast_mouse_mode.py
            with delay_callback(state, 'bias', 'contrast'):
                state.bias = -(x * 2 - 1.5)
                state.contrast = 10. ** (y * 2 - 1)

            self._time_last = time.time()

        elif event == 'dblclick':
            # When blinked, first layer might not be top layer
            i_top = get_top_layer_index(self.viewer)
            state = self.viewer.layers[i_top].state

            # Restore defaults that are applied on load
            with delay_callback(state, 'bias', 'contrast'):
                state.bias = 0.5
                state.contrast = 1
