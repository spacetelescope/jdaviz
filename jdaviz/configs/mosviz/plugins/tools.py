import os

from glue.config import viewer_tool

from jdaviz.core.tools import HomeZoom, BoxZoom, XRangeZoom, PanZoom, PanZoomX

__all__ = []

ICON_DIR = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'data', 'icons')


@viewer_tool
class MosvizHomeZoom(HomeZoom):
    icon = os.path.join(ICON_DIR, 'home_match.svg')
    tool_id = 'mosviz:homezoom'
    action_text = 'Reset zoom'
    tool_tip = 'Reset zoom to show all visible data, matching x-limits in all viewers'


@viewer_tool
class MosvizBoxZoom(BoxZoom):
    icon = os.path.join(ICON_DIR, 'zoom_box_match.svg')
    tool_id = 'mosviz:boxzoom'
    action_text = 'Box zoom, matching x-limits between viewers'
    tool_tip = 'Zoom to a drawn rectangle, matching x-limits in all viewers'


@viewer_tool
class MosvizXRangeZoom(XRangeZoom):
    icon = os.path.join(ICON_DIR, 'zoom_xrange_match.svg')
    tool_id = 'mosviz:xrangezoom'
    action_text = 'Horizontal zoom, matching x-limits between viewers'
    tool_tip = 'Zoom to a drawn horizontal region, matching x-limits in all viewers'


@viewer_tool
class MosvizPanZoom(PanZoom):
    icon = os.path.join(ICON_DIR, 'panzoom_match.svg')
    tool_id = 'mosviz:panzoom'
    action_text = 'Pan, matching x-limits between viewers'
    tool_tip = 'Pan (click-drag) or zoom (scroll), matching x-limits in all viewers'  # noqa


@viewer_tool
class MosvizPanZoomX(PanZoomX):
    icon = os.path.join(ICON_DIR, 'pan_x_match.svg')
    tool_id = 'mosviz:panzoom_x'
    action_text = 'Pan, matching x-limits between viewers'
    tool_tip = 'Pan (click-drag) or zoom (scroll) in x only, matching limits in all viewers'  # noqa
