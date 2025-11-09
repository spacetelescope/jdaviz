import os
from pathlib import Path
from traitlets import Unicode, Bool

from glue_jupyter.common.toolbar_vuetify import read_icon

from jdaviz.core.registries import loader_resolver_registry
from jdaviz.core.loaders.resolvers import BaseResolver
from jdaviz.core.user_api import LoaderUserApi
from jdaviz.core.template_mixin import CustomToolbarToggleMixin
from jdaviz.core.tools import ICON_DIR


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
class ObjectResolver(BaseResolver, CustomToolbarToggleMixin):
    template_file = __file__, "object.vue"
    default_input = 'object'
    requires_api_support = True

    object_repr = Unicode("").tag(sync=True)
    is_wcs_linked = Bool(False).tag(sync=True)
    footprint_select_icon = Unicode(read_icon(os.path.join(
        ICON_DIR, 'footprint_select.svg'), 'svg+xml')).tag(sync=True)

    def __init__(self, *args, **kwargs):
        self._object = None
        super().__init__(*args, **kwargs)

        if self.app is not None:
            self.is_wcs_linked = getattr(self.app, '_align_by', None) == 'wcs'
        def custom_toolbar(viewer):
            if hasattr(self, 'observation_table') and self.observation_table is not None:
                if 's_region' in self.observation_table.headers_avail:
                    return viewer.toolbar._original_tools_nested[:3] + [['jdaviz:selectregion']], 'jdaviz:selectregion'
            return None, None

        self.custom_toolbar.callable = custom_toolbar
        self.custom_toolbar.name = "Footprint Selection"

    def toggle_custom_toolbar(self):
        """Override to control footprint display when toolbar is toggled."""
        super().toggle_custom_toolbar()

    def vue_link_by_wcs(self, *args):
        """Link images by WCS using the Imviz helper."""
        self.app._jdaviz_helper.link_data(align_by='wcs')
        self.is_wcs_linked = True

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
