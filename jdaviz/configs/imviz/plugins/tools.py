import os

from echo import delay_callback

from glue.config import viewer_tool
from glue.viewers.common.tool import CheckableTool
from glue_jupyter.bqplot.image import BqplotImageView
from glue_jupyter.utils import debounced

from jdaviz.core.tools import BoxZoom, PanZoom, _MatchedZoomMixin

__all__ = []

ICON_DIR = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'data', 'icons')


class _ImvizMatchedZoomMixin(_MatchedZoomMixin):
    match_keys = ('x_min', 'x_max', 'y_min', 'y_max')
    disable_matched_zoom_in_other_viewer = False

    def _is_matched_viewer(self, viewer):
        return isinstance(viewer, BqplotImageView)

    def _post_activate(self):
        # NOTE: For Imviz only.
        # Set the reference data in other viewers to be the same as the current viewer.
        # If adding the data to the viewer, make sure it is not actually shown since the
        # user didn't request it.
        for viewer in self._iter_matched_viewers(include_self=False):
            if self.viewer.state.reference_data not in viewer.state.layers_data:
                viewer.add_data(self.viewer.state.reference_data)
                for layer in viewer.state.layers:
                    if layer.layer is self.viewer.state.reference_data:
                        layer.visible = False
                        break
            viewer.state.reference_data = self.viewer.state.reference_data


@viewer_tool
class ImagePanZoom(PanZoom):
    tool_id = 'jdaviz:imagepanzoom'
    tool_tip = 'Interactively pan (click-drag), zoom (scroll), and center (click)'

    def activate(self):
        super().activate()
        self.viewer.add_event_callback(self.on_click, events=['click'])

    def deactivate(self):
        self.viewer.remove_event_callback(self.on_click)
        super().deactivate()

    def on_click(self, data):
        # Find visible layers
        visible_layers = [layer for layer in self.viewer.state.layers if layer.visible]
        if len(visible_layers) == 0:
            return

        # Same data as mousemove event in Imviz viewer.
        # Any other config that wants this functionality has to have the following:
        #   viewer._get_real_xy()
        #   viewer.center_on() --> inherited from AstrowidgetsImageViewerMixin
        image = visible_layers[0].layer
        x = data['domain']['x']
        y = data['domain']['y']
        if x is None or y is None:  # Out of bounds
            return
        x, y, _, _ = self.viewer._get_real_xy(image, x, y)
        self.viewer.center_on((x, y))


@viewer_tool
class BlinkOnce(CheckableTool):
    icon = os.path.join(ICON_DIR, 'blink.svg')
    tool_id = 'jdaviz:blinkonce'
    action_text = 'Go to next image'
    tool_tip = ('Click on the viewer or press "b" to display the next image, '
                'or right-click or press "B" to display the previous')

    def activate(self):
        self.viewer.add_event_callback(self.on_click, events=['click', 'contextmenu'])

    def deactivate(self):
        self.viewer.remove_event_callback(self.on_click)

    def on_click(self, data):
        self.viewer.blink_once(reversed=data['event']=='contextmenu')  # noqa: E225

    def is_visible(self):
        return len(self.viewer.state.layers) > 1


@viewer_tool
class MatchBoxZoom(_ImvizMatchedZoomMixin, BoxZoom):
    icon = os.path.join(ICON_DIR, 'zoom_box_match.svg')
    tool_id = 'jdaviz:boxzoommatch'
    action_text = 'Box zoom, matching between viewers'
    tool_tip = 'Zoom to a drawn rectangle in all viewers'


@viewer_tool
class MatchPanZoom(_ImvizMatchedZoomMixin, ImagePanZoom):
    icon = os.path.join(ICON_DIR, 'panzoom_match.svg')
    tool_id = 'jdaviz:panzoommatch'
    action_text = 'Pan, matching between viewers'
    tool_tip = 'Pan (click-drag), zoom (scroll), and center (click) in this viewer to see the same regions in other viewers'  # noqa


@viewer_tool
class ContrastBias(CheckableTool):

    icon = os.path.join(ICON_DIR, 'contrast.svg')
    tool_id = 'jdaviz:contrastbias'
    action_text = 'Adjust contrast/bias'
    tool_tip = 'Click and drag to adjust contrast and bias, double-click to reset'

    def __init__(self, viewer, **kwargs):
        super().__init__(viewer, **kwargs)

    def activate(self):
        self.viewer.add_event_callback(self.on_mouse_or_key_event,
                                       events=['dragstart', 'dragmove',
                                               'dblclick'])

    def deactivate(self):
        self.viewer.remove_event_callback(self.on_mouse_or_key_event)

    @debounced(delay_seconds=0.03, method=True)
    def _dragevent(self, data):
        event_x = data['pixel']['x']
        event_y = data['pixel']['y']

        if ((event_x < 0) or (event_x >= self._max_x) or
                (event_y < 0) or (event_y >= self._max_y)):
            return

        # Normalize w.r.t. viewer display from 0 to 1
        # Also see glue/viewers/matplotlib/qt/toolbar_mode.py
        # bias range 0..1
        # contrast range 0..4
        bias = event_x / (self._max_x - 1)
        contrast = 4 * (1 - (event_y / (self._max_y - 1)))

        with delay_callback(self._layer_state, 'bias', 'contrast'):
            self._layer_state.bias = bias
            self._layer_state.contrast = contrast

    def on_mouse_or_key_event(self, data):
        from jdaviz.configs.imviz.helper import get_top_layer_index

        event = data['event']

        if event == 'dragstart':
            # When blinked, first layer might not be top layer
            # TODO: could optimize this further by listening for changes to the layers
            # and viewer size rather than having to set this on the dragstart event
            i_top = get_top_layer_index(self.viewer)
            state = self.viewer.layers[i_top].state
            self._layer_state = state
            self._max_x = self.viewer.shape[1]
            self._max_y = self.viewer.shape[0]
        elif event == 'dragmove':
            self._dragevent(data)
        elif event == 'dblclick':
            # Restore defaults that are applied on load
            i_top = get_top_layer_index(self.viewer)
            state = self.viewer.layers[i_top].state
            with delay_callback(state, 'bias', 'contrast'):
                state.bias = 0.5
                state.contrast = 1
