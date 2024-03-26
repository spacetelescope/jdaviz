import os
import time

import numpy as np
from echo import delay_callback
from glue.config import viewer_tool
from glue.core import HubListener
from glue.viewers.common.tool import Tool
from glue_jupyter.bqplot.common.tools import (CheckableTool,
                                              HomeTool, BqplotPanZoomMode,
                                              BqplotPanZoomXMode, BqplotPanZoomYMode,
                                              BqplotRectangleMode, BqplotCircleMode,
                                              BqplotEllipseMode, BqplotCircularAnnulusMode,
                                              BqplotXRangeMode, BqplotYRangeMode,
                                              BqplotSelectionTool,
                                              INTERACT_COLOR)
from bqplot.interacts import BrushSelector, BrushIntervalSelector

from jdaviz.core.events import LineIdentifyMessage, SpectralMarksChangedMessage
from jdaviz.core.marks import SpectralLine

__all__ = []

ICON_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', 'data', 'icons'))


# Override icons for built-in tools from glue-jupyter
BqplotRectangleMode.icon = os.path.join(ICON_DIR, 'select_xy.svg')
BqplotCircleMode.icon = os.path.join(ICON_DIR, 'select_circle.svg')
BqplotEllipseMode.icon = os.path.join(ICON_DIR, 'select_ellipse.svg')
BqplotCircularAnnulusMode.icon = os.path.join(ICON_DIR, 'select_annulus.svg')
BqplotXRangeMode.icon = os.path.join(ICON_DIR, 'select_x.svg')
BqplotYRangeMode.icon = os.path.join(ICON_DIR, 'select_y.svg')


class _BaseZoomHistory:
    # Mixin for custom zoom tools to be able to save their previous zoom state
    # which is then used by the PrevZoom tool
    def save_prev_zoom(self):
        self.viewer._prev_limits = (self.viewer.state.x_min, self.viewer.state.x_max,
                                    self.viewer.state.y_min, self.viewer.state.y_max)


class _MatchedZoomMixin:
    match_axes = ('x', 'y')
    disable_matched_zoom_in_other_viewer = True

    def _is_matched_viewer(self, viewer):
        return True

    def _iter_matched_viewers(self, include_self=False):
        for viewer in self.viewer.session.application.viewers:
            if viewer is self.viewer and not include_self:
                continue
            elif self._is_matched_viewer(viewer):
                yield viewer

    def _map_limits(self, from_viewer, to_viewer, limits={}):
        return limits

    @property
    def match_keys(self):
        keys = []
        for ax in self.match_axes:
            keys += [f'{ax}_min', f'{ax}_max']
        return keys

    def activate(self):
        if self.disable_matched_zoom_in_other_viewer:
            # mapping limits are not guaranteed to roundtrip, so we need to disable
            # any linked tool in the "other" viewer
            for viewer in self._iter_matched_viewers(include_self=False):
                if isinstance(viewer.toolbar.active_tool, _MatchedZoomMixin):
                    viewer.toolbar.active_tool_id = None

        super().activate()
        for k in self.match_keys:
            self.viewer.state.add_callback(k, self.on_limits_change)

        # Trigger a sync so the initial limits match
        self.on_limits_change()

    def deactivate(self):
        for k in self.match_keys:
            self.viewer.state.remove_callback(k, self.on_limits_change)

        super().deactivate()

    def on_limits_change(self, *args):
        # from_lims: limits in the viewer belonging to the tool
        from_lims = {k: getattr(self.viewer.state, k) for k in self.match_keys}
        orig_refdata = self.viewer.state.reference_data
        if hasattr(self.viewer, '_get_fov') and orig_refdata and orig_refdata.coords:
            orig_fov_sky = self.viewer._get_fov(wcs=orig_refdata.coords)
            sky_cen = self.viewer._get_center_skycoord()
        else:
            orig_fov_sky = sky_cen = None

        for viewer in self._iter_matched_viewers(include_self=False):
            # orig_lims: limits in this "matched" viewer
            # to_lims: proposed new limits for this "matched" viewer
            orig_lims = {k: getattr(viewer.state, k) for k in self.match_keys}
            to_lims = self._map_limits(self.viewer, viewer, from_lims)
            matched_refdata = viewer.state.reference_data

            if hasattr(viewer, '_get_fov'):
                to_fov_sky = viewer._get_fov(wcs=matched_refdata.coords)
            else:
                to_fov_sky = None

            if to_fov_sky is not None and orig_fov_sky is not None:
                old_level = viewer.zoom_level
                viewer.zoom_level = old_level * float(to_fov_sky / orig_fov_sky)
                viewer.center_on(sky_cen)

            else:
                with delay_callback(viewer.state, *self.match_keys):
                    for ax in self.match_axes:
                        if None in orig_lims.values():
                            orig_range = np.inf
                        else:
                            orig_range = abs(orig_lims.get(f'{ax}_max') -
                                             orig_lims.get(f'{ax}_min'))
                        to_range = abs(to_lims.get(f'{ax}_max') -
                                       to_lims.get(f'{ax}_min'))
                        tol = 1e-6 * min(orig_range, to_range)

                        for k in (f'{ax}_min', f'{ax}_max'):
                            value = to_lims.get(k)
                            orig_value = orig_lims.get(k)

                            if not np.isnan(value) and (orig_value is None or
                                                        abs(value-orig_lims.get(k, np.inf)) > tol):
                                setattr(viewer.state, k, value)

    def is_visible(self):
        return len(self.viewer.jdaviz_app._viewer_store) > 1


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
class YRangeZoom(_BaseSelectZoom):
    icon = os.path.join(ICON_DIR, 'zoom_yrange.svg')
    tool_id = 'jdaviz:yrangezoom'
    action_text = 'Vertical zoom'
    tool_tip = 'Zoom to a drawn vertical region'

    def _new_interact(self):
        return BrushIntervalSelector(orientation='vertical',
                                     scale=self.viewer.scale_y,
                                     color=INTERACT_COLOR)

    def on_update_zoom(self):
        if self.interact.selected is None:
            # a valid region was not drawn, perhaps just a click with no drag!
            # let's ignore and reset the tool
            return

        self.viewer.state.y_min, self.viewer.state.y_max = self.interact.selected


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

    def is_visible(self):
        return len([m for m in self.viewer.figure.marks if isinstance(m, SpectralLine)]) > 0


@viewer_tool
class StretchBounds(CheckableTool):
    icon = os.path.join(ICON_DIR, 'stretch_bounds.svg')
    tool_id = 'jdaviz:stretch_bounds'
    action_text = 'Set Stretch VMin and VMax'
    tool_tip = 'Set closest stretch bound (VMin/VMax) with click or click+drag'

    def __init__(self, viewer, **kwargs):
        self._time_last = 0
        super().__init__(viewer, **kwargs)

    def activate(self):
        self.viewer.add_event_callback(self.on_mouse_event,
                                       events=['dragmove', 'click'])
        for mark in self.viewer.figure.marks:
            if np.any([x in mark.labels for x in ('vmin', 'vmax', 'stretch_knots')]):
                mark.colors = ["#c75d2c"]

    def deactivate(self):
        self.viewer.remove_event_callback(self.on_mouse_event)
        for mark in self.viewer.figure.marks:
            if np.any([x in mark.labels for x in ('vmin', 'vmax', 'stretch_knots')]):
                mark.colors = ["#007BA1"]

    def on_mouse_event(self, data):
        if (time.time() - self._time_last) <= 0.02:
            # throttle to 200ms
            return

        # Mouse event coordinates
        event_x = data['domain']['x']
        event_y = data['domain']['y']

        x_min, x_max = self.viewer.state.x_min, self.viewer.state.x_max
        y_min, y_max = self.viewer.state.y_min, self.viewer.state.y_max

        current_bounds = [self.viewer._plugin.stretch_vmin_value,
                          self.viewer._plugin.stretch_vmax_value]

        vmin_normalized = (current_bounds[0] - x_min) / (x_max - x_min)
        vmax_normalized = (current_bounds[1] - x_min) / (x_max - x_min)
        event_x_normalized = (event_x - x_min) / (x_max - x_min)

        distances_to_bounds_normalized = [abs(vmin_normalized - event_x_normalized), abs(vmax_normalized - event_x_normalized)]  # noqa
        closest_bound_index = np.argmin(distances_to_bounds_normalized)
        closest_bound_distance = distances_to_bounds_normalized[closest_bound_index]

        stretch_type = self.viewer._plugin.stretch_function_value
        if stretch_type == 'spline':
            # Retrieve current knots and bounds
            # knots_x is in units of the x-axis (pixel value)
            knots_x = self.viewer._plot.marks['stretch_knots'].x
            # knots_y is in units of the (hidden) normalized y-axis from 0 to 1
            knots_y = self.viewer._plot.marks['stretch_knots'].y

            # event_y is in units of the y-axis (density),
            # so we need to rescale event_y to the same units as knots_y
            event_y_normalized = (event_y - y_min) / (y_max - y_min)
            # Drop event if the event coordinate are out of bounds
            if not 0 <= event_y_normalized <= 0.9:
                return

            # Distance from mouse position to each knot, normalized to viewer axes size
            distances_to_knots = np.sqrt(((knots_x - event_x) / (x_max - x_min)) ** 2 +
                                         ((knots_y - event_y_normalized)) ** 2)

            # we don't consider the first or last knot
            # as those should remain anchored to 0 and 1, respectively
            knot_index_by_dist = np.argsort(distances_to_knots[1:-1]) + 1
            closest_knot_index = knot_index_by_dist[0]
            closest_knot_distance = distances_to_knots[closest_knot_index]

            radius_threshold = 0.1
            x_distance_threshold = 0.1
            if closest_knot_distance > radius_threshold and closest_bound_distance > x_distance_threshold:  # noqa
                return
            if closest_knot_distance < radius_threshold:
                if distances_to_knots[knot_index_by_dist[1]] < radius_threshold:
                    # don't allow knots getting too close to each other
                    return
                if knots_x[closest_knot_index-1] >= event_x or knots_x[closest_knot_index+1] <= event_x:  # noqa
                    return
                # knots_x and event_x are in units of the x-axis (pixel value)
                knots_x[closest_knot_index] = event_x
                # knots_y and event_y_data_units are in units of the y-axis (density)
                knots_y[closest_knot_index] = event_y_normalized
                # knot_x now needs to be mapped from the x-axis to the range 0-1
                # that the stretch class expects (where 0
                # corresponds to vmin and 1 to vmax)
                stretch_x = (knots_x - current_bounds[0]) / (current_bounds[1] - current_bounds[0])   # noqa
                stretch_y = knots_y / 0.9
                self.viewer._plugin.stretch_params_value = {'knots': (stretch_x.tolist(), stretch_y.tolist())}  # noqa
            else:
                if closest_bound_distance > x_distance_threshold:
                    return
                att_names = ["stretch_vmin_value", "stretch_vmax_value"][closest_bound_index]
                setattr(self.viewer._plugin, att_names, event_x)
        else:
            att_names = ["stretch_vmin_value", "stretch_vmax_value"][closest_bound_index]
            setattr(self.viewer._plugin, att_names, event_x)

        self._time_last = time.time()


class _BaseSidebarShortcut(Tool):
    plugin_name = None  # define in subclass
    viewer_attr = 'viewer'

    def activate(self):
        plugin = self.viewer.jdaviz_app.get_tray_item_from_name(self.plugin_name)
        plugin.open_in_tray(scroll_to=True)
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
    plugin_name = 'export'

    icon = os.path.join(ICON_DIR, 'image.svg')
    tool_id = 'jdaviz:sidebar_export'
    action_text = 'Export plot'
    tool_tip = 'Open export plugin in sidebar'


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
