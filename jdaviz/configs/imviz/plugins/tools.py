import time
import os

from echo import delay_callback

from glue.config import viewer_tool
from glue.viewers.common.tool import CheckableTool
from glue_jupyter.bqplot.common.tools import BqplotPanZoomMode

from jdaviz.core.tools import BoxZoom

__all__ = []

ICON_DIR = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'data', 'icons')


class _MatchedZoomMixin:
    def activate(self):

        super().activate()

        self.viewer.state.add_callback('x_min', self.on_limits_change)
        self.viewer.state.add_callback('x_max', self.on_limits_change)
        self.viewer.state.add_callback('y_min', self.on_limits_change)
        self.viewer.state.add_callback('y_max', self.on_limits_change)

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
class BlinkOnce(CheckableTool):
    icon = os.path.join(ICON_DIR, 'blink.svg')
    tool_id = 'jdaviz:blinkonce'
    action_text = 'Go to next image'
    tool_tip = ('Click on the viewer to display the next image, '
                'or you can also press the "b" key anytime')

    def activate(self):
        self.viewer.add_event_callback(self.on_click,
                                       events=['click'])

    def deactivate(self):
        self.viewer.remove_event_callback(self.on_click)

    def on_click(self, *args):
        self.viewer.blink_once()


@viewer_tool
class MatchBoxZoom(_MatchedZoomMixin, BoxZoom):
    icon = os.path.join(ICON_DIR, 'zoom_box_match.svg')
    tool_id = 'jdaviz:boxzoommatch'
    action_text = 'Box zoom, matching between viewers'
    tool_tip = 'Zoom to a drawn rectangle in all viewers'


@viewer_tool
class MatchPanZoom(_MatchedZoomMixin, BqplotPanZoomMode):
    icon = os.path.join(ICON_DIR, 'panzoom_match.svg')
    tool_id = 'jdaviz:panzoommatch'
    action_text = 'Pan, matching between viewers'
    tool_tip = 'Pan (click-drag) and Zoom (scroll) in this viewer to see the same regions in other viewers'  # noqa


@viewer_tool
class ContrastBias(CheckableTool):

    icon = os.path.join(ICON_DIR, 'contrast.svg')
    tool_id = 'jdaviz:contrastbias'
    action_text = 'Adjust contrast/bias'
    tool_tip = 'Click and drag to adjust contrast and bias, double-click to reset'

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

            event_x = data['pixel']['x']
            event_y = data['pixel']['y']
            max_x = self.viewer.shape[1]
            max_y = self.viewer.shape[0]

            if ((event_x < 0) or (event_x >= max_x) or
                    (event_y < 0) or (event_y >= max_y)):
                return

            # Normalize w.r.t. viewer display from 0 to 1
            x = event_x / (max_x - 1)
            y = event_y / (max_y - 1)

            # When blinked, first layer might not be top layer
            i_top = get_top_layer_index(self.viewer)
            state = self.viewer.layers[i_top].state

            # bias range 0..1
            # contrast range 0..4
            with delay_callback(state, 'bias', 'contrast'):
                state.bias = x
                state.contrast = y * 4

            self._time_last = time.time()

        elif event == 'dblclick':
            # When blinked, first layer might not be top layer
            i_top = get_top_layer_index(self.viewer)
            state = self.viewer.layers[i_top].state

            # Restore defaults that are applied on load
            with delay_callback(state, 'bias', 'contrast'):
                state.bias = 0.5
                state.contrast = 1
