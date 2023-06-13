import os

from glue.config import viewer_tool

from jdaviz.configs.mosviz.plugins.viewers import MosvizProfileView, MosvizProfile2DView
from jdaviz.core.tools import _MatchedZoomMixin, HomeZoom, BoxZoom, XRangeZoom, PanZoom, PanZoomX

__all__ = []

ICON_DIR = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'data', 'icons')


class _MatchedXZoomMixin(_MatchedZoomMixin):
    match_axes = ('x',)
    disable_matched_zoom_in_other_viewer = True

    def _is_matched_viewer(self, viewer):
        return isinstance(viewer, (MosvizProfile2DView, MosvizProfileView))

    def _map_limits(self, from_viewer, to_viewer, limits={}):
        if isinstance(from_viewer, MosvizProfileView) and isinstance(to_viewer, MosvizProfile2DView):  # noqa
            limits['x_min'], limits['x_max'] = to_viewer.world_to_pixel_limits((limits['x_min'],
                                                                                limits['x_max']))
        elif isinstance(from_viewer, MosvizProfile2DView) and isinstance(to_viewer, MosvizProfileView):  # noqa
            limits['x_min'], limits['x_max'] = from_viewer.pixel_to_world_limits((limits['x_min'],
                                                                                  limits['x_max']))
        return limits


@viewer_tool
class MosvizHomeZoom(_MatchedXZoomMixin, HomeZoom):
    icon = os.path.join(ICON_DIR, 'home_match.svg')
    tool_id = 'mosviz:homezoom'
    action_text = 'Reset zoom'
    tool_tip = 'Reset zoom to show all visible data, matching x-limits in all viewers'


@viewer_tool
class MosvizBoxZoom(_MatchedXZoomMixin, BoxZoom):
    icon = os.path.join(ICON_DIR, 'zoom_box_match.svg')
    tool_id = 'mosviz:boxzoom'
    action_text = 'Box zoom, matching x-limits between viewers'
    tool_tip = 'Zoom to a drawn rectangle, matching x-limits in all viewers'


@viewer_tool
class MosvizXRangeZoom(_MatchedXZoomMixin, XRangeZoom):
    icon = os.path.join(ICON_DIR, 'zoom_xrange_match.svg')
    tool_id = 'mosviz:xrangezoom'
    action_text = 'Horizontal zoom, matching x-limits between viewers'
    tool_tip = 'Zoom to a drawn horizontal region, matching x-limits in all viewers'


@viewer_tool
class MosvizPanZoom(_MatchedXZoomMixin, PanZoom):
    icon = os.path.join(ICON_DIR, 'panzoom_match.svg')
    tool_id = 'mosviz:panzoom'
    action_text = 'Pan, matching x-limits between viewers'
    tool_tip = 'Pan (click-drag) or zoom (scroll), matching x-limits in all viewers'  # noqa


@viewer_tool
class MosvizPanZoomX(_MatchedXZoomMixin, PanZoomX):
    icon = os.path.join(ICON_DIR, 'pan_x_match.svg')
    tool_id = 'mosviz:panzoom_x'
    action_text = 'Pan, matching x-limits between viewers'
    tool_tip = 'Pan (click-drag) or zoom (scroll) in x only, matching limits in all viewers'  # noqa
