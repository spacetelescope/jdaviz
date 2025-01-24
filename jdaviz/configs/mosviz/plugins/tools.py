import os

from glue.config import viewer_tool
from astropy import units as u

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
        components = self.viewer.state.data_collection[0]._components
        # Determine cid for spectral axis
        for key in components.keys():
            strkey = str(key)
            if 'Wavelength' in strkey or 'Wave' in strkey:
                native_unit = u.Unit(self.viewer.state.data_collection[0].get_component(strkey).units)  # noqa
                break
        else:
            # no matches found
            native_unit = ''
        current_display_unit = u.Unit(self.viewer.jdaviz_helper.app._get_display_unit('spectral'))

        if isinstance(from_viewer, MosvizProfileView) and isinstance(to_viewer, MosvizProfile2DView):  # noqa
            if native_unit != current_display_unit and native_unit != '':
                limits['x_min'] = (limits['x_min'] * native_unit).to_value(
                                   current_display_unit, equivalencies=u.spectral()
                                )
                limits['x_max'] = (limits['x_max'] * native_unit).to_value(
                                   current_display_unit, equivalencies=u.spectral()
                                   )
            limits['x_min'], limits['x_max'] = to_viewer.world_to_pixel_limits((limits['x_min'],
                                                                                limits['x_max']))
        elif isinstance(from_viewer, MosvizProfile2DView) and isinstance(to_viewer, MosvizProfileView):  # noqa
            limits['x_min'], limits['x_max'] = from_viewer.pixel_to_world_limits((limits['x_min'],
                                                                                  limits['x_max']))
            if native_unit != current_display_unit and native_unit != '':
                limits['x_min'] = (limits['x_min'] * native_unit).to_value(
                                   current_display_unit, equivalencies=u.spectral()
                                   )
                limits['x_max'] = (limits['x_max'] * native_unit).to_value(
                                   current_display_unit, equivalencies=u.spectral()
                                   )
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
