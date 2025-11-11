import os
from pathlib import Path

import numpy as np
from glue.core import HubListener
from glue_jupyter.common.toolbar_vuetify import read_icon
from traitlets import Unicode, Bool

from jdaviz.core.events import RegionSelectClickEventMessage
from jdaviz.core.marks import RegionOverlay
from jdaviz.core.registries import loader_resolver_registry
from jdaviz.core.loaders.resolvers import BaseResolver
from jdaviz.core.user_api import LoaderUserApi
from jdaviz.core.template_mixin import CustomToolbarToggleMixin
from jdaviz.core.tools import ICON_DIR
from jdaviz.core.region_translators import is_stcs_string, stcs_string2region


def closest_point_on_segment(px, py, x1, y1, x2, y2):
    """
    Find the closest points on a line segment to a given point.

    Parameters
    ----------
    px : float
        X coordinate of the reference point.
    py : float
        Y coordinate of the reference point.
    x1, y1 : numpy.ndarray
        Coordinates of the starting points of the segments.
    x2, y2 : numpy.ndarray
        Coordinates of the ending points of the segments.

    Returns
    -------
    closest_xs : numpy.ndarray
        The x coordinates of the closest points on the segments.
    closest_ys : numpy.ndarray
        The y coordinates of the closest points on the segments.

    """

    dx, dy = x2 - x1, y2 - y1
    denominator = dx ** 2 + dy ** 2
    # Calculate t: how far along the segment the projection of the point falls
    t = ((px - x1) * dx + (py - y1) * dy) / np.where(denominator == 0, 1, denominator)
    t = np.where(denominator == 0, 0, t)  # Handle zero-length segments
    t = np.clip(t, 0, 1)
    closest_xs = x1 + t * dx
    closest_ys = y1 + t * dy
    return closest_xs, closest_ys


def find_closest_polygon_mark(px, py, marks):
    """
    Find the closest mark to a click point and return its observation index.

    Parameters
    ----------
    px : float
        X coordinate of the reference point.
    py : float
        Y coordinate of the reference point.
    marks : list of RegionOverlay
        List of mark objects to compare against the given point.

    Returns
    -------
    closest_idx : int or None
        The observation index of the closest mark, or None if no marks.
    """
    min_dist = float('inf')
    closest_idx = None

    for mark in marks:
        x_coords = np.array(mark.x)
        y_coords = np.array(mark.y)

        if len(x_coords) == 0 or len(y_coords) == 0:
            continue

        x1 = x_coords
        x2 = np.roll(x_coords, -1)
        y1 = y_coords
        y2 = np.roll(y_coords, -1)

        closest_xs, closest_ys = closest_point_on_segment(px, py, x1, y1, x2, y2)
        dist = (closest_xs - px)**2 + (closest_ys - py)**2

        min_idx = np.argmin(dist)
        min_dist_for_this_mark = dist[min_idx]

        if min_dist_for_this_mark < min_dist:
            min_dist = min_dist_for_this_mark
            # Extract observation index from overlay name format
            closest_idx = int(mark._overlay.split('_')[-1])

    return closest_idx


@loader_resolver_registry('object')
class ObjectResolver(BaseResolver, CustomToolbarToggleMixin, HubListener):
    template_file = __file__, "object.vue"
    default_input = 'object'
    requires_api_support = True

    object_repr = Unicode("").tag(sync=True)
    is_wcs_linked = Bool(False).tag(sync=True)
    footprint_select_icon = Unicode(read_icon(os.path.join(
        ICON_DIR, 'footprint_select.svg'), 'svg+xml')).tag(sync=True)

    def __init__(self, *args, **kwargs):
        self._object = None
        self._footprint_marks = []
        # Mapping observation idx to list of marks
        self._footprint_groups = {}
        super().__init__(*args, **kwargs)

        if self.app is not None:
            self.is_wcs_linked = getattr(self.app, '_align_by', None) == 'wcs'
            self.app.hub.subscribe(self, RegionSelectClickEventMessage,
                                   handler=self._on_region_select)

        def custom_toolbar(viewer):
            if self.observation_table_populated and 's_region' in self.observation_table.headers_avail:  # noqa: E501
                return viewer.toolbar._original_tools_nested[:3] + [['jdaviz:selectregion']], 'jdaviz:selectregion'  # noqa: E501
            return None, None

        self.custom_toolbar.callable = custom_toolbar
        self.custom_toolbar.name = "Footprint Selection"

    def toggle_custom_toolbar(self):
        """Override to control footprint display when toolbar is toggled."""
        if not self.custom_toolbar_enabled:
            self._display_observation_footprints()
            super().toggle_custom_toolbar()
        else:
            super().toggle_custom_toolbar()
            self._remove_observation_footprints()

    def vue_link_by_wcs(self, *args):
        """Link images by WCS."""
        self.app._jdaviz_helper.link_data(align_by='wcs')
        self.is_wcs_linked = True

    def _on_region_select(self, msg):
        if not self._footprint_marks:
            return

        click_x, click_y = msg.x, msg.y
        selected_idx = find_closest_polygon_mark(click_x, click_y, self._footprint_marks)

        if selected_idx is not None:
            # Get selected rows from the table
            currently_selected = set()
            if hasattr(self, 'observation_table') and self.observation_table is not None:
                for row in self.observation_table.selected_rows:
                    idx = self.observation_table.items.index(row)
                    currently_selected.add(idx)

            # Toggle behavior
            if selected_idx in currently_selected:
                currently_selected.discard(selected_idx)
                for mark in self._footprint_groups.get(selected_idx, []):
                    mark.selected = False
            else:
                currently_selected.add(selected_idx)
                if selected_idx in self._footprint_groups:
                    for mark in self._footprint_groups[selected_idx]:
                        mark.selected = True

            # Update the table selection
            if hasattr(self, 'observation_table') and self.observation_table is not None:
                if currently_selected:
                    self.observation_table.select_rows(sorted(list(currently_selected)))
                else:
                    # Clear selection
                    self.observation_table.selected_rows = []

    def _display_observation_footprints(self):
        if 's_region' not in self.observation_table.headers_avail:
            return

        viewer = self.app._jdaviz_helper.default_viewer._obj.glue_viewer
        wcs = getattr(viewer.state.reference_data, 'coords', None)

        successfully_displayed = 0
        new_marks = []

        for idx, row in enumerate(self.observation_table.items):
            s_region_str = row.get('s_region', '')

            if not s_region_str or (isinstance(s_region_str, str) and s_region_str.strip() == ''):
                continue
            if not is_stcs_string(s_region_str):
                continue

            region = stcs_string2region(s_region_str)
            pixel_region = region.to_pixel(wcs)
            x, y = pixel_region.vertices.x, pixel_region.vertices.y

            mark = RegionOverlay(
                viewer,
                f"ObsTable_{idx}",
                x=x, y=y,
                fill_opacities=[0],
                label=f"ObsTable_{idx}",
                selected=False
            )
            new_marks.append(mark)
            self._footprint_marks.append(mark)
            self._footprint_groups[idx] = [mark]
            successfully_displayed += 1

        # Add all marks at once
        if new_marks:
            viewer.figure.marks = list(viewer.figure.marks) + new_marks

    def _remove_observation_footprints(self):
        if not self._footprint_marks:
            return

        viewer = self.app._jdaviz_helper.default_viewer._obj.glue_viewer
        current_marks = list(viewer.figure.marks)

        for mark in self._footprint_marks:
            if mark in current_marks:
                current_marks.remove(mark)

        viewer.figure.marks = current_marks
        self._footprint_marks = []
        self._footprint_groups = {}

    def on_observation_select_changed(self, msg=None):
        """Override to sync footprint selection when table rows are selected."""
        super().on_observation_select_changed(msg)

        if not self._footprint_groups:
            return

        selected_indices = set()
        for row in self.observation_table.selected_rows:
            idx = self.observation_table.items.index(row)
            selected_indices.add(idx)

        # Update footprint marks based on selection
        for idx, marks in self._footprint_groups.items():
            selected = idx in selected_indices
            for mark in marks:
                mark.selected = selected

    @property
    def user_api(self):
        return LoaderUserApi(self, expose=['object'])

    @property
    def is_valid(self):
        if isinstance(self.object, str):
            # reject strings that should go through file
            # or url resolvers instead
            if Path(self.object).exists():
                return False
            if self.object.strip().startswith(('http://', 'https://',
                                               'ftp://', 's3://', 'mast://')):
                return False
        return not isinstance(self.object, Path)

    @property
    def object(self):
        return self._object

    @object.setter
    def object(self, obj):
        self._object = obj
        self.object_repr = f"<{obj.__class__.__name__} object>"
        self._resolver_input_updated()

    def parse_input(self):
        return self.object
