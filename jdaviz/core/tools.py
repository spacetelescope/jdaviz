import os
import time

import numpy as np
from astropy.coordinates import SkyCoord
from astropy import units as u
from echo import delay_callback
from functools import cached_property
from glue.config import viewer_tool
from glue.core import HubListener
from glue.viewers.common.tool import Tool
from glue_jupyter.bqplot.common import tools
from glue_jupyter.bqplot.common.tools import (CheckableTool,
                                              HomeTool, BqplotPanZoomMode,
                                              BqplotPanZoomXMode, BqplotPanZoomYMode,
                                              BqplotRectangleMode, BqplotCircleMode,
                                              BqplotEllipseMode, BqplotCircularAnnulusMode,
                                              BqplotXRangeMode, BqplotYRangeMode,
                                              BqplotSelectionTool)
from bqplot.interacts import BrushSelector, BrushIntervalSelector

from jdaviz.core.events import (LineIdentifyMessage, SpectralMarksChangedMessage,
                                CatalogSelectClickEventMessage, FootprintSelectClickEventMessage,
                                FootprintOverlayClickMessage, TableSelectRowClickMessage)
from jdaviz.core.marks import SpectralLine, FootprintOverlay, RegionOverlay
from jdaviz.utils import get_top_layer_index, in_ra_comps, in_dec_comps

__all__ = []

INTERACT_COLOR = "#c75109"
tools.INTERACT_COLOR = INTERACT_COLOR
ICON_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', 'data', 'icons'))


# Override icons for built-in tools from glue-jupyter
BqplotRectangleMode.icon = os.path.join(ICON_DIR, 'select_xy.svg')
BqplotCircleMode.icon = os.path.join(ICON_DIR, 'select_circle.svg')
BqplotEllipseMode.icon = os.path.join(ICON_DIR, 'select_ellipse.svg')
BqplotCircularAnnulusMode.icon = os.path.join(ICON_DIR, 'select_annulus.svg')
BqplotXRangeMode.icon = os.path.join(ICON_DIR, 'select_x.svg')
BqplotYRangeMode.icon = os.path.join(ICON_DIR, 'select_y.svg')


def _get_skycoords_from_table(layer, rows=None):
    """
    Get SkyCoord for rows in a table layer.

    First checks for RA/Dec column names stored in metadata by the catalog importer,
    then falls back to flexible name matching.

    Parameters
    ----------
    layer : glue Data
        The table data layer
    rows : array-like, optional
        Row indices to select. If None, returns all rows.

    Returns
    -------
    SkyCoord or None
        SkyCoord for the selected rows, or None if RA/Dec columns not found.
    """
    ra_comp = None
    dec_comp = None

    # First, check if the catalog importer stored the RA/Dec column names in metadata
    ra_col_name = layer.meta.get('_jdaviz_loader_ra_col')
    dec_col_name = layer.meta.get('_jdaviz_loader_dec_col')

    if ra_col_name and dec_col_name:
        # Find the component IDs that match these column names
        for comp_id in layer.component_ids():
            comp_name = str(comp_id)
            if comp_name == ra_col_name:
                ra_comp = comp_id
            elif comp_name == dec_col_name:
                dec_comp = comp_id

    # Fall back to flexible name matching if metadata not found or columns not matched
    if ra_comp is None or dec_comp is None:
        for comp_id in layer.component_ids():
            comp_name = str(comp_id)
            if in_ra_comps(comp_name) and ra_comp is None:
                ra_comp = comp_id
            elif in_dec_comps(comp_name) and dec_comp is None:
                dec_comp = comp_id

    if ra_comp is None or dec_comp is None:
        return None

    try:
        ras = layer.get_component(ra_comp).data
        decs = layer.get_component(dec_comp).data

        if rows is not None:
            ras = ras[rows]
            decs = decs[rows]

        return SkyCoord(ra=ras * u.deg, dec=decs * u.deg)
    except Exception:
        return None


class _BaseZoomHistory:
    # Mixin for custom zoom tools to be able to save their previous zoom state
    # which is then used by the PrevZoom tool
    def save_prev_zoom(self):
        # Cannot use viewer.get_limits() here because viewers from
        # glue-jupyter does not have that method.
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

    @cached_property
    def delay_callback_keys(self):
        all_keys = ['x_min', 'x_max', 'y_min', 'y_max',
                    'zoom_center_x', 'zoom_center_y', 'zoom_radius']
        return [k for k in all_keys
                if np.all([hasattr(v.state, k)
                           for v in self._iter_matched_viewers(include_self=True)])]

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

            if hasattr(viewer, '_get_fov') and matched_refdata is not None:
                to_fov_sky = viewer._get_fov(wcs=matched_refdata.coords)
            else:
                to_fov_sky = None

            if to_fov_sky is not None and orig_fov_sky is not None:
                old_level = viewer.zoom_level
                viewer.zoom_level = old_level * float(to_fov_sky / orig_fov_sky)
                viewer.center_on(sky_cen)

            elif len(self.match_axes):
                with delay_callback(viewer.state, *self.delay_callback_keys):
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
            else:
                # match keys, but not match axes (e.g., zoom_center and zoom_radius)
                with delay_callback(viewer.state, *self.delay_callback_keys):
                    for k in self.match_keys:
                        value = to_lims.get(k)
                        if not np.isnan(value):
                            setattr(viewer.state, k, value)

    def is_visible(self):
        return (len(self.viewer.jdaviz_app._viewer_store) > 1
                and len(list(self._iter_matched_viewers())) > 0)


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
        with delay_callback(self.viewer.state, 'x_min', 'x_max', 'y_min', 'y_max'):
            self.viewer.state.x_min, self.viewer.state.x_max, self.viewer.state.y_min, self.viewer.state.y_max = prev_limits  # noqa


@viewer_tool
class HomeZoom(HomeTool, _BaseZoomHistory):
    icon = os.path.join(ICON_DIR, 'home.svg')
    tool_id = 'jdaviz:homezoom'
    action_text = 'Reset zoom'
    tool_tip = 'Reset zoom to show all visible data'

    def activate(self):
        self.save_prev_zoom()

        # typical case:
        if not hasattr(self.viewer, 'reset_limits'):
            super().activate()
        else:
            # if the viewer has its own reset_limits method, use it:
            self.viewer.reset_limits()


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
class ViewerClone(Tool):
    icon = os.path.join(ICON_DIR, 'viewer_clone')
    tool_id = 'jdaviz:viewer_clone'
    action_text = 'Clone viewer'
    tool_tip = 'Clone this viewer'

    def activate(self):
        self.viewer.clone_viewer()

    def is_visible(self):
        return self.viewer.jdaviz_app.config not in ['specviz', 'specviz2d',
                                                     'cubeviz', 'mosviz',
                                                     'rampviz']


class _BaseTableSelectionTool(Tool):
    """
    Base class for table tools that enable row selection checkboxes and swap the toolbar.

    Subclasses should define:
    - icon, tool_id, action_text, tool_tip
    - override_tools: list of tool IDs to show in the custom toolbar
    - override_title: title for the custom toolbar
    - image_viewer_override_tools: tools to show in image viewer toolbars when this tool is active
    """
    override_tools = []  # define in subclass
    override_title = ''  # define in subclass
    # Tools to show in image viewer toolbars when this tool is activated
    image_viewer_override_tools = [
        ['jdaviz:homezoom'],
        ['jdaviz:boxzoom'],
        ['jdaviz:imagepanzoom'],
        ['jdaviz:select_table_row']
    ]

    def _get_image_viewers(self):
        """Get list of image viewers."""
        return list(self.viewer.jdaviz_app.get_viewers_of_cls('ImvizImageView'))

    def get_custom_widgets(self):
        """
        Override in subclass to return list of custom widget dicts for the toolbar.
        Currently only implemented for dropdowns, but could be extended in the future.
        Each dict should have: 'label', 'items' (list of {'label', 'value'}),
        'selected', 'multiselect'
        """
        return None

    def activate(self):
        # Show checkboxes (they're hidden by default and should be hidden when toolbar restores)
        self.viewer.widget_table.selection_enabled = True

        # Override toolbar to show custom tools
        # Pass callback for dynamic widget updates (e.g., when viewers are added/removed)
        custom_widgets = self.get_custom_widgets()
        custom_widgets_callback = self.get_custom_widgets if custom_widgets else None
        self.viewer.toolbar.override_tools(
            self.override_tools,
            self.override_title,
            custom_widgets=custom_widgets,
            custom_widgets_callback=custom_widgets_callback
        )

        # Also override toolbars in all image viewers
        for image_viewer in self._get_image_viewers():
            # Set the table viewer ID on the select_table_row tool so it knows
            # which table viewer to send the message to
            image_viewer.toolbar.override_tools(
                self.image_viewer_override_tools,
                self.override_title,
                active_tool='jdaviz:select_table_row'
            )
            # Configure the select_table_row tool with this table viewer's ID
            # for now we'll hardcode this, but could generalize if there are cases
            # where we want other default tools in the future
            if 'jdaviz:select_table_row' in image_viewer.toolbar.tools:
                tool = image_viewer.toolbar.tools['jdaviz:select_table_row']
                tool._table_viewer_id = self.viewer.reference_id


class _BaseTableApplyTool(Tool):
    """
    Base class for table tools that apply an action and restore the toolbar.

    Subclasses should define:
    - icon, tool_id, action_text, tool_tip (as usual for tools)
    - on_apply(selected_rows): method to perform the action (only called if rows are selected)
    """

    def on_apply(self, selected_rows):
        """Override in subclass to perform the action with the selected rows."""
        pass

    def activate(self):
        selected_rows = self.viewer.widget_table.checked

        if len(selected_rows):
            self.on_apply(selected_rows)

        # Hide checkboxes (they should always be hidden when default toolbar is shown)
        self.viewer.widget_table.selection_enabled = False
        # Clear checked rows after applying
        self.viewer.widget_table.checked = []
        # Restore toolbar (all_viewers=True to also restore image viewer toolbars)
        self.viewer.toolbar.restore_tools(all_viewers=True)


@viewer_tool
class TableHighlightSelected(_BaseTableSelectionTool):
    icon = os.path.join(ICON_DIR, 'table-eye.svg')
    tool_id = 'jdaviz:table_highlight_selected'
    action_text = 'Highlight selected'
    tool_tip = 'Enable row selection mode to highlight checked entries in image viewers'
    override_tools = []  # just the close button
    override_title = 'Table Highlight Selection'

    def _get_image_viewers(self):
        """Get list of image viewers that can show highlights."""
        return list(self.viewer.jdaviz_app.get_viewers_of_cls('ImvizImageView'))

    def is_visible(self):
        if self.viewer.jdaviz_app.config != 'deconfigged':
            return False
        if not len(self._get_image_viewers()):
            return False
        if not hasattr(self.viewer, 'widget_table'):
            return False
        return True


@viewer_tool
class TableSubset(_BaseTableSelectionTool):
    icon = os.path.join(ICON_DIR, 'table_subset.svg')
    tool_id = 'jdaviz:table_subset'
    action_text = 'Create subset from table selection'
    tool_tip = 'Enable row selection mode to create a subset from table rows'
    override_tools = ['jdaviz:table_apply_subset']
    override_title = 'Table Subset Selection'

    def is_visible(self):
        if self.viewer.jdaviz_app.config != 'deconfigged':
            return False
        if not hasattr(self.viewer, 'widget_table'):
            return False
        return True


@viewer_tool
class TableApplySubset(_BaseTableApplyTool):
    icon = os.path.join(ICON_DIR, 'check.svg')
    tool_id = 'jdaviz:table_apply_subset'
    action_text = 'Apply subset'
    tool_tip = 'Create a subset from the currently checked table rows'

    def on_apply(self, selected_rows):
        self.viewer.apply_filter()

    def is_visible(self):
        if self.viewer.jdaviz_app.config != 'deconfigged':
            return False
        if not hasattr(self.viewer, 'widget_table'):
            return False
        return True

    def disabled_msg(self):
        if not len(self.viewer.widget_table.checked):
            return 'Select rows to create subset'
        return ''


@viewer_tool
class TableZoomToSelected(_BaseTableSelectionTool):
    icon = os.path.join(ICON_DIR, 'table_zoom_to_selected.svg')
    tool_id = 'jdaviz:table_zoom_to_selected'
    action_text = 'Zoom to selected'
    tool_tip = 'Enable row selection mode to zoom all applicable viewers to checked entries'
    override_tools = ['jdaviz:table_apply_zoom']
    override_title = 'Table Zoom Selection'

    def _get_image_viewers(self):
        """Get list of image viewers that can be zoomed."""
        return list(self.viewer.jdaviz_app.get_viewers_of_cls('ImvizImageView'))

    def get_custom_widgets(self):
        """Return viewer selector widget configuration."""
        image_viewers = self._get_image_viewers()
        if not image_viewers:
            return None

        # Build items list from available image viewers
        items = [
            {'label': v.reference_id, 'value': v.reference_id}
            for v in image_viewers
        ]
        # Default to all viewers selected
        selected = [v.reference_id for v in image_viewers]

        return [{
            'label': 'Viewers',
            'items': items,
            'selected': selected,
            'multiselect': True
        }]

    def is_visible(self):
        if self.viewer.jdaviz_app.config != 'deconfigged':
            return False
        if not len(self._get_image_viewers()):
            return False
        if not hasattr(self.viewer, 'widget_table'):
            return False
        return True


@viewer_tool
class TableApplyZoom(_BaseTableApplyTool):
    icon = os.path.join(ICON_DIR, 'check.svg')
    tool_id = 'jdaviz:table_apply_zoom'
    action_text = 'Apply zoom'
    tool_tip = 'Zoom all applicable viewers to the currently checked table rows'

    def on_apply(self, selected_rows):
        layer = self.viewer.layers[0].layer
        skycoords = _get_skycoords_from_table(layer, selected_rows)
        if skycoords is None:
            return

        # Get the selected viewer IDs from the custom widget
        if len(self.viewer.toolbar.custom_widget_selected) > 0:
            selected_viewer_ids = self.viewer.toolbar.custom_widget_selected[0]
        else:
            # no selected viewers, do nothing
            return

        for viewer in self.viewer.jdaviz_app.get_viewers_of_cls('ImvizImageView'):
            # Skip viewers not in the selection (if selection exists)
            if viewer.reference_id not in selected_viewer_ids:
                continue

            i_top = get_top_layer_index(viewer)
            if i_top is None:
                continue
            image = viewer.layers[i_top].layer

            # Get pixel coordinates in the TOP LAYER's coordinate system
            # (this is what center_on expects)
            if hasattr(image, 'coords') and image.coords is not None:
                pixel_coords = image.coords.world_to_pixel(skycoords)
                xs, ys = np.atleast_1d(pixel_coords[0]), np.atleast_1d(pixel_coords[1])
            else:
                # No WCS on top layer, skip this viewer
                continue

            # Filter out NaN values
            valid = np.isfinite(xs) & np.isfinite(ys)
            if not np.any(valid):
                continue
            xs, ys = xs[valid], ys[valid]

            # Calculate center in top layer coordinates
            x_center = 0.5 * (np.min(xs) + np.max(xs))
            y_center = 0.5 * (np.min(ys) + np.max(ys))

            # Calculate radius as max distance from center to any point
            # This ensures all points are visible
            distances = np.sqrt((xs - x_center)**2 + (ys - y_center)**2)
            radius = np.max(distances) if len(distances) > 0 else 0

            # For single point or very close points, use a minimum radius
            if radius < 20:
                radius = 20

            # Add 20% padding
            radius *= 1.2

            # Center on the middle point (in top layer coordinates)
            viewer.center_on((x_center, y_center))

            # Now convert center and radius to reference data coordinates for zoom
            # Get center in reference data coordinates
            ref_center = viewer._get_real_xy(image, x_center, y_center, reverse=True)

            # Get a point at the edge to determine radius in reference coordinates
            # We need to check both x and y directions in case of rotation/scale differences
            ref_x_edge = viewer._get_real_xy(image, x_center + radius, y_center, reverse=True)
            ref_y_edge = viewer._get_real_xy(image, x_center, y_center + radius, reverse=True)

            # Calculate effective radius in reference coordinates
            ref_radius_x = abs(ref_x_edge[0] - ref_center[0])
            ref_radius_y = abs(ref_y_edge[1] - ref_center[1])
            ref_radius = max(ref_radius_x, ref_radius_y)

            # Set Y limits (most displays are wider, so fit Y first)
            # Then _adjust_limits_aspect will expand X as needed
            new_y_min = ref_center[1] - ref_radius
            new_y_max = ref_center[1] + ref_radius

            with delay_callback(viewer.state, 'x_min', 'x_max', 'y_min', 'y_max'):
                viewer.state.y_min = new_y_min
                viewer.state.y_max = new_y_max
            viewer.state._adjust_limits_aspect()

    def is_visible(self):
        if self.viewer.jdaviz_app.config != 'deconfigged':
            return False
        if not len(self.viewer.jdaviz_app.get_viewers_of_cls('ImvizImageView')):
            return False
        if not hasattr(self.viewer, 'widget_table'):
            return False
        return True

    def disabled_msg(self):
        if not len(self.viewer.widget_table.checked):
            return 'Select rows to zoom'
        return ''


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
        # ensure self.line_marks is populated
        self.viewer._broadcast_plotted_lines()
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
class SelectCatalogMark(CheckableTool, HubListener):
    icon = os.path.join(ICON_DIR, 'catalog_select.svg')
    tool_id = 'jdaviz:selectcatalog'
    action_text = 'Select/identify source from catalog'
    tool_tip = 'Select/identify source from catalog'

    def __init__(self, viewer, **kwargs):
        super().__init__(viewer, **kwargs)
        self.xs = []
        self.ys = []

    def activate(self):
        self.viewer.add_event_callback(self.on_mouse_event,
                                       events=['click'])

    def deactivate(self):
        self.viewer.remove_event_callback(self.on_mouse_event)

    def on_mouse_event(self, data):
        msg = CatalogSelectClickEventMessage(data['domain']['x'], data['domain']['y'], sender=self)
        self.viewer.session.hub.broadcast(msg)

    def is_visible(self):
        # NOTE: this assumes Catalogs._marker_name remains fixed at the default of 'catalog_results'
        return 'catalog_results' in [dci.label for dci in self.viewer.jdaviz_app.data_collection]


@viewer_tool
class SelectTableRow(CheckableTool, HubListener):
    """Tool for selecting/toggling the closest table row from an image viewer click."""
    icon = os.path.join(ICON_DIR, 'catalog_select.svg')
    tool_id = 'jdaviz:select_table_row'
    action_text = 'Select/toggle table row'
    tool_tip = 'Click to select/toggle the closest table row'

    # This will be set when the tool is activated via override_tools
    _table_viewer_id = None

    def activate(self):
        self.viewer.add_event_callback(self.on_mouse_event, events=['click'])

    def deactivate(self):
        self.viewer.remove_event_callback(self.on_mouse_event)

    def on_mouse_event(self, data):
        if self._table_viewer_id is None:
            return
        msg = TableSelectRowClickMessage(
            data['domain']['x'],
            data['domain']['y'],
            self._table_viewer_id,
            sender=self
        )
        self.viewer.session.hub.broadcast(msg)


@viewer_tool
class SelectFootprintOverlay(CheckableTool, HubListener):
    icon = os.path.join(ICON_DIR, 'footprint_select.svg')
    tool_id = 'jdaviz:selectfootprint'
    action_text = 'Select/identify overlay'
    tool_tip = 'Select/identify overlay'

    def activate(self):
        self.viewer.add_event_callback(self.on_mouse_event,
                                       events=['click'])

    def deactivate(self):
        self.viewer.remove_event_callback(self.on_mouse_event)

    def on_mouse_event(self, data):
        msg = FootprintSelectClickEventMessage(data, sender=self)
        self.viewer.session.hub.broadcast(msg)

    def is_visible(self):
        return any(
            isinstance(m, FootprintOverlay) and m.visible
            for m in self.viewer.figure.marks
            )


@viewer_tool
class SkewerSelectRegion(CheckableTool, HubListener):
    icon = os.path.join(ICON_DIR, 'skewer_select.svg')
    tool_id = 'jdaviz:skewerregion'
    action_text = 'Select/identify smallest region containing cursor'
    tool_tip = 'Select/identify smallest region containing cursor'

    def activate(self):
        self.viewer.add_event_callback(self.on_mouse_event,
                                       events=['click'])

    def deactivate(self):
        self.viewer.remove_event_callback(self.on_mouse_event)

    def on_mouse_event(self, data):
        msg = FootprintOverlayClickMessage(data, mode="skewer", sender=self)
        self.viewer.session.hub.broadcast(msg)

    def is_visible(self):
        return any(isinstance(m, RegionOverlay) and m.visible
                   for m in self.viewer.figure.marks)


@viewer_tool
class SelectRegionOverlay(CheckableTool, HubListener):
    icon = os.path.join(ICON_DIR, 'footprint_select.svg')
    tool_id = 'jdaviz:selectregion'
    action_text = 'Select/identify region overlay'
    tool_tip = 'Select/identify region overlay'

    def activate(self):
        self.viewer.add_event_callback(self.on_mouse_event,
                                       events=['click'])

    def deactivate(self):
        self.viewer.remove_event_callback(self.on_mouse_event)

    def on_mouse_event(self, data):
        msg = FootprintOverlayClickMessage(data, mode="nearest", sender=self)
        self.viewer.session.hub.broadcast(msg)

    def is_visible(self):
        return any(
            isinstance(m, RegionOverlay) and m.visible
            for m in self.viewer.figure.marks
            )


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

    icon = os.path.join(ICON_DIR, 'cog.svg')
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
            self.viewer.jdaviz_app.get_tray_item_from_name('g-subset-tools').combination_mode.selected = 'new'  # noqa
            self.viewer.jdaviz_app.get_tray_item_from_name('g-subset-tools').import_region(
                reg, return_bad_regions=True)
            self.viewer.jdaviz_app.get_tray_item_from_name('g-subset-tools').combination_mode.selected = 'replace'  # noqa

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
