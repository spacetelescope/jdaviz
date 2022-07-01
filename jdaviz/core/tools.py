import numpy as np
import os
from echo import delay_callback

from glue.config import viewer_tool
from glue.core import HubListener
from glue.viewers.common.tool import Tool
from glue_jupyter.bqplot.common.tools import (CheckableTool, HomeTool, BqplotPanZoomMode,
                                              BqplotPanZoomXMode, BqplotPanZoomYMode,
                                              BqplotRectangleMode, BqplotCircleMode,
                                              BqplotEllipseMode, BqplotXRangeMode,
                                              BqplotYRangeMode, BqplotSelectionTool,
                                              INTERACT_COLOR)
from bqplot.interacts import BrushSelector, BrushIntervalSelector

from jdaviz.core.events import LineIdentifyMessage, SpectralMarksChangedMessage

__all__ = []

ICON_DIR = os.path.join(os.path.dirname(__file__), '..', 'data', 'icons')


# Override icons for built-in tools from glue-jupyter
BqplotRectangleMode.icon = os.path.join(ICON_DIR, 'select_xy.svg')
BqplotCircleMode.icon = os.path.join(ICON_DIR, 'select_circle.svg')
BqplotEllipseMode.icon = os.path.join(ICON_DIR, 'select_ellipse.svg')
BqplotXRangeMode.icon = os.path.join(ICON_DIR, 'select_x.svg')
BqplotYRangeMode.icon = os.path.join(ICON_DIR, 'select_y.svg')


class _BaseZoomHistory:
    # Mixin for custom zoom tools to be able to save their previous zoom state
    # which is then used by the PrevZoom tool
    def save_prev_zoom(self):
        self.viewer._prev_limits = (self.viewer.state.x_min, self.viewer.state.x_max,
                                    self.viewer.state.y_min, self.viewer.state.y_max)


@viewer_tool
class PrevZoom(Tool, _BaseZoomHistory):
    icon = os.path.join(ICON_DIR, 'zoom_back.svg')
    tool_id = 'jdaviz:prevzoom'
    action_text = 'Previous zoom'
    tool_tip = 'Back to previous zoom level'

    def activate(self):
        if self.viewer._prev_limits is None:
            return
        prev_limits = self.viewer._prev_limits
        self.save_prev_zoom()
        self.viewer.state.x_min, self.viewer.state.x_max, self.viewer.state.y_min, self.viewer.state.y_max = prev_limits  # noqa


@viewer_tool
class HomeZoom(HomeTool, _BaseZoomHistory):
    icon = os.path.join(ICON_DIR, 'home.svg')
    tool_id = 'jdaviz:homezoom'
    action_text = 'Reset zoom'
    tool_tip = 'Reset zoom to show all visible data'

    def activate(self):
        self.save_prev_zoom()
        super().activate()


@viewer_tool
class PanZoom(BqplotPanZoomMode, _BaseZoomHistory):
    icon = os.path.join(ICON_DIR, 'pan.svg')
    tool_id = 'jdaviz:panzoom'

    def activate(self):
        self.save_prev_zoom()
        super().activate()


@viewer_tool
class PanZoomX(BqplotPanZoomXMode, _BaseZoomHistory):
    icon = os.path.join(ICON_DIR, 'pan_x.svg')
    tool_id = 'jdaviz:panzoom_x'

    def activate(self):
        self.save_prev_zoom()
        super().activate()


@viewer_tool
class PanZoomY(BqplotPanZoomYMode, _BaseZoomHistory):
    icon = os.path.join(ICON_DIR, 'pan_y.svg')
    tool_id = 'jdaviz:panzoom_y'

    def activate(self):
        self.save_prev_zoom()
        super().activate()


class _BaseSelectZoom(BqplotSelectionTool, _BaseZoomHistory):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.reset()

    def _new_interact(self):
        raise NotImplementedError(f"_new_interact not implemented by {self.__class__.__name__}")

    def reset(self):
        if hasattr(self, 'interact'):
            self.interact.close()
        self.interact = self._new_interact()
        self.interact.observe(self.on_brushing, "brushing")

    def on_brushing(self, msg):
        if self.interact.brushing:
            # start drawing a box, don't need to do anything
            return

        self.save_prev_zoom()

        with delay_callback(self.viewer.state, 'x_min', 'x_max', 'y_min', 'y_max'):
            # implement on_update_zoom to act on the applicable interact Selector
            self.on_update_zoom()

        # reset destroys the current interact and replaces with a new one to avoid having
        # the draggable selection
        self.reset()
        # activate automatically activates the new interact so that another zoom is possible
        # until deselecting the zoom tool
        self.activate()


@viewer_tool
class BoxZoom(_BaseSelectZoom):
    icon = os.path.join(ICON_DIR, 'zoom_box.svg')
    tool_id = 'jdaviz:boxzoom'
    action_text = 'Box zoom'
    tool_tip = 'Zoom to a drawn rectangle'

    def _new_interact(self):
        return BrushSelector(x_scale=self.viewer.scale_x,
                             y_scale=self.viewer.scale_y,
                             color=INTERACT_COLOR)

    def on_update_zoom(self):
        if self.interact.selected_x is None or self.interact.selected_y is None:
            # a valid box was not drawn, perhaps just a click with no drag!
            # let's ignore and reset the tool
            return

        self.viewer.state.x_min, self.viewer.state.x_max = self.interact.selected_x
        self.viewer.state.y_min, self.viewer.state.y_max = self.interact.selected_y


@viewer_tool
class XRangeZoom(_BaseSelectZoom):
    icon = os.path.join(ICON_DIR, 'zoom_xrange.svg')
    tool_id = 'jdaviz:xrangezoom'
    action_text = 'Horizontal zoom'
    tool_tip = 'Zoom to a drawn horizontal region'

    def _new_interact(self):
        return BrushIntervalSelector(scale=self.viewer.scale_x,
                                     color=INTERACT_COLOR)

    def on_update_zoom(self):
        if self.interact.selected is None:
            # a valid region was not drawn, perhaps just a click with no drag!
            # let's ignore and reset the tool
            return

        self.viewer.state.x_min, self.viewer.state.x_max = self.interact.selected


@viewer_tool
class SelectLine(CheckableTool, HubListener):
    icon = os.path.join(ICON_DIR, 'line_select.svg')
    tool_id = 'jdaviz:selectline'
    action_text = 'Select/identify spectral line'
    tool_tip = 'Select/identify spectral line'

    def __init__(self, viewer, **kwargs):
        super().__init__(viewer, **kwargs)
        self.line_marks = []
        self.line_names = []

        self.viewer.session.hub.subscribe(self, SpectralMarksChangedMessage,
                                          handler=self._on_plotted_lines_changed)

    def activate(self):
        self.viewer.add_event_callback(self.on_mouse_event,
                                       events=['click'])

    def deactivate(self):
        self.viewer.remove_event_callback(self.on_mouse_event)

    def _on_plotted_lines_changed(self, msg):
        self.line_marks = msg.marks
        self.line_names = msg.names_rest

    def on_mouse_event(self, data):
        # yes this would be avoid a list-comprehension by putting in
        # _on_plotted_lines_changed, but by leaving it here, we let
        # the marks worry about unit conversions
        lines_x = np.array([mark.obs_value for mark in self.line_marks])
        if not len(lines_x):
            return
        ind = np.argmin(abs(lines_x - data['domain']['x']))
        # find line closest to mouse position and transmit event
        msg = LineIdentifyMessage(self.line_names[ind], sender=self)
        self.viewer.session.hub.broadcast(msg)


class _BaseSidebarShortcut(Tool):
    plugin_name = None  # define in subclass
    viewer_attr = 'viewer'

    def activate(self):
        jdaviz_state = self.viewer.jdaviz_app.state
        jdaviz_state.drawer = True
        tray_item_names = [tray_item['name'] for tray_item in jdaviz_state.tray_items]
        index = tray_item_names.index(self.plugin_name)
        if index not in jdaviz_state.tray_items_open:
            jdaviz_state.tray_items_open = jdaviz_state.tray_items_open + [index]
        plugin = self.viewer.jdaviz_app.get_tray_item_from_name(self.plugin_name)
        viewer_id = self.viewer.reference_id
        viewer_select = getattr(plugin, self.viewer_attr)
        if viewer_select.multiselect:
            viewer_id = [viewer_id]
        setattr(viewer_select, 'selected', viewer_id)


@viewer_tool
class SidebarShortcutPlotOptions(_BaseSidebarShortcut):
    plugin_name = 'g-plot-options'

    icon = os.path.join(ICON_DIR, 'tune.svg')
    tool_id = 'jdaviz:sidebar_plot'
    action_text = 'Plot Options'
    tool_tip = 'Open plot options plugin in sidebar'


@viewer_tool
class SidebarShortcutExportPlot(_BaseSidebarShortcut):
    plugin_name = 'g-export-plot'

    icon = os.path.join(ICON_DIR, 'image.svg')
    tool_id = 'jdaviz:sidebar_export'
    action_text = 'Export plot'
    tool_tip = 'Open export plot plugin in sidebar'


@viewer_tool
class SidebarShortcutCompass(_BaseSidebarShortcut):
    plugin_name = 'imviz-compass'

    icon = os.path.join(ICON_DIR, 'compass.svg')
    tool_id = 'jdaviz:sidebar_compass'
    action_text = 'Compass'
    tool_tip = 'Open compass plugin in sidebar'
