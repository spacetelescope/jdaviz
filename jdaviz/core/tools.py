import os

import numpy as np
from echo import delay_callback
from glue.config import viewer_tool
from glue.core import HubListener
from glue.core.edit_subset_mode import ReplaceMode
from glue.core.roi import CircularROI, EllipticalROI, RectangularROI
from glue.core.subset import RoiSubsetState
from glue.viewers.common.tool import Tool
from glue_astronomy.translators.regions import _annulus_to_subset_state
from glue_jupyter.bqplot.common.tools import (CheckableTool,
                                              HomeTool, BqplotPanZoomMode,
                                              BqplotPanZoomXMode, BqplotPanZoomYMode,
                                              BqplotRectangleMode, BqplotCircleMode,
                                              BqplotEllipseMode, BqplotXRangeMode,
                                              BqplotYRangeMode, BqplotSelectionTool,
                                              INTERACT_COLOR)
from bqplot.interacts import BrushSelector, BrushIntervalSelector
from regions import CircleAnnulusPixelRegion, PixCoord

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

        new_interact_x = self.get_x_axis_with_aspect_ratio()
        self.viewer.state.y_min, self.viewer.state.y_max = self.interact.selected_y

        # Change the x axis to make sure all y axis values from the box zoom are included
        self.viewer.state.x_min, self.viewer.state.x_max = new_interact_x

    def get_x_axis_with_aspect_ratio(self):
        new_interact_x = self.interact.selected_x
        # If aspect is equal, then we need to preserve that aspect ratio
        # even if the box zoom area does not.
        if self.viewer.state.aspect == "equal":
            fig_axes_ratio = ((self.viewer.state.x_max - self.viewer.state.x_min) /
                              (self.viewer.state.y_max - self.viewer.state.y_min))

            # The value at index of 1 will always be the larger of the two numbers
            x_diff = self.interact.selected_x[1] - self.interact.selected_x[0]
            y_diff = self.interact.selected_y[1] - self.interact.selected_y[0]

            if x_diff < y_diff * fig_axes_ratio:
                x_with_aspect = y_diff * fig_axes_ratio
                x_centre = (self.interact.selected_x[0] + self.interact.selected_x[1]) / 2
                new_interact_x = (x_centre - x_with_aspect / 2, x_centre + x_with_aspect / 2)

        return new_interact_x


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
        plugin = self.viewer.jdaviz_app.get_tray_item_from_name(self.plugin_name)
        plugin.open_in_tray()
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


@viewer_tool
class SinglePixelRegion(CheckableTool):

    icon = os.path.join(ICON_DIR, 'select_single_pixel.svg')
    tool_id = 'jdaviz:singlepixelregion'
    action_text = 'Create single-pixel spatial region'
    tool_tip = 'Define a single-pixel spatial region of interest'

    def activate(self):
        # This is copied from glue-jupyter's BqplotSelectionTool (but we don't inherit
        # from that because that in turn inherits from InteractCheckableTool which requires
        # setting self.interact)
        if self.viewer.session.application.get_setting('new_subset_on_selection_tool_change'):
            self.viewer.session.edit_subset_mode.edit_subset = None

        self.viewer.add_event_callback(self.on_mouse_event, events=['click'])

    def deactivate(self):
        self.viewer.remove_event_callback(self.on_mouse_event)

    def on_mouse_event(self, data):
        # Extract data coordinates - these are pixels in the reference image.
        # NOTE: We always use the reference image pixel coordinates because
        # Subset is defined w.r.t. reference image.
        x = data['domain']['x']
        y = data['domain']['y']

        if data['altKey'] is True:
            reg = self.get_subset(x, y, as_roi=False)
            self.viewer.jdaviz_helper.load_regions(reg)
        else:
            roi = self.get_subset(x, y, as_roi=True)
            self.viewer.apply_roi(roi)

    def get_subset(self, x, y, as_roi=False):
        from regions import RectanglePixelRegion, PixCoord
        x, y = np.rint([x, y])  # Center on nearest pixel
        reg = RectanglePixelRegion(center=PixCoord(x=x, y=y), width=1, height=1)

        if as_roi:
            from jdaviz.core.region_translators import regions2roi
            roi = regions2roi(reg)
            return roi

        return reg


@viewer_tool
class ClickToMoveSpatialRegion(CheckableTool):

    icon = os.path.join(ICON_DIR, 'pan.svg')  # TODO: New icon?
    tool_id = 'jdaviz:clicktomovespatialregion'
    action_text = 'Move a spatial region'
    tool_tip = 'Click to move a spatial region selected in Subset Tools'

    def activate(self):
        # This is copied from glue-jupyter's BqplotSelectionTool (but we don't inherit
        # from that because that in turn inherits from InteractCheckableTool which requires
        # setting self.interact)
        self.viewer.add_event_callback(self.on_mouse_event, events=['click'])

    def deactivate(self):
        self.viewer.remove_event_callback(self.on_mouse_event)

    def on_mouse_event(self, data):
        subset_plg = self.viewer.jdaviz_helper.plugins["Subset Tools"]._obj
        if subset_plg.subset_selected == 'Create New':
            return

        # Extract data coordinates - these are pixels in the reference image.
        # NOTE: We always use the reference image pixel coordinates because
        # Subset is defined w.r.t. reference image.
        x = data['domain']['x']
        y = data['domain']['y']

        subset_state = subset_plg.subset_select.selected_subset_state
        subset_state.move_to(x, y)

        # Force glue to update the Subset. This is the same call used in
        # glue.core.edit_subset_mode.EditSubsetMode.update() but we do not
        # want to deal with all the contract stuff tied to the update() method.
        self.viewer.session.edit_subset_mode._combine_data(subset_state, override_mode=ReplaceMode)


@viewer_tool
class ClickToCreateCircularAnnulus(CheckableTool):

    icon = 'glue_spawn'  # TODO: New icon?
    tool_id = 'jdaviz:clicktocreatecircularannulus'
    action_text = 'Create a circular annulus'
    tool_tip = 'Click to create a circular annulus based on a selected region in Subset Tools'

    def activate(self):
        # This is copied from glue-jupyter's BqplotSelectionTool (but we don't inherit
        # from that because that in turn inherits from InteractCheckableTool which requires
        # setting self.interact)
        self.viewer.add_event_callback(self.on_mouse_event, events=['click'])

    def deactivate(self):
        self.viewer.remove_event_callback(self.on_mouse_event)

    def on_mouse_event(self, data):
        subset_plg = self.viewer.jdaviz_helper.plugins["Subset Tools"]._obj
        if subset_plg.subset_selected == 'Create New':
            return

        subset_state = subset_plg.subset_select.selected_subset_state
        if not isinstance(subset_state, RoiSubsetState):
            return

        roi = subset_state.roi
        if isinstance(roi, CircularROI):
            inner_r = roi.radius
        elif isinstance(roi, EllipticalROI):
            inner_r = max(roi.radius_x, roi.radius_y)
        elif isinstance(roi, RectangularROI):
            inner_r = max(roi.width(), roi.height()) * 0.5
        else:
            return

        # Hardcode the outer radius for now. Hopefully can edit in Subset Tools later.
        outer_r = inner_r + 5

        # Extract data coordinates - these are pixels in the reference image.
        # NOTE: We always use the reference image pixel coordinates because
        # Subset is defined w.r.t. reference image.
        x = data['domain']['x']
        y = data['domain']['y']

        reg = CircleAnnulusPixelRegion(
            center=PixCoord(x=x, y=y), inner_radius=inner_r, outer_radius=outer_r)
        annulus_sbst = _annulus_to_subset_state(reg, self.viewer.state.reference_data)

        # Create new annulus subset.
        self.viewer.session.application.data_collection.new_subset_group(subset_state=annulus_sbst)
