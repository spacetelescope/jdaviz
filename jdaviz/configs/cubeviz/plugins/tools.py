import time
import os

from glue.config import viewer_tool
from glue_jupyter.bqplot.image import BqplotImageView
from glue.viewers.common.tool import CheckableTool
import numpy as np
from specutils import Spectrum1D

from jdaviz.core.events import SliceToolStateMessage, SliceSelectSliceMessage
from jdaviz.core.tools import PanZoom, BoxZoom, _MatchedZoomMixin
from jdaviz.configs.default.plugins.tools import ProfileFromCube

__all__ = []

ICON_DIR = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'data', 'icons')


class _PixelMatchedZoomMixin(_MatchedZoomMixin):
    match_axes = []
    disable_matched_zoom_in_other_viewer = True

    @property
    def match_keys(self):
        return ['zoom_center_x', 'zoom_center_y', 'zoom_radius']

    def _is_matched_viewer(self, viewer):
        return isinstance(viewer, BqplotImageView)


@viewer_tool
class PixelMatchPanZoom(_PixelMatchedZoomMixin, PanZoom):
    """Like MatchPanZoom in Imviz but without complicated
    WCS linking logic because it is not needed for Cubeviz.
    """
    icon = os.path.join(ICON_DIR, 'panzoom_match.svg')
    tool_id = 'jdaviz:pixelpanzoommatch'
    action_text = 'Pan, matching between viewers'
    tool_tip = 'Pan (click-drag) and zoom (scroll) in this viewer to see the same regions in other viewers'  # noqa


@viewer_tool
class PixelMatchBoxZoom(_PixelMatchedZoomMixin, BoxZoom):
    """Like MatchBoxZoom in Imviz but without complicated
    WCS linking logic because it is not needed for Cubeviz.
    """
    icon = os.path.join(ICON_DIR, 'zoom_box_match.svg')
    tool_id = 'jdaviz:pixelboxzoommatch'
    action_text = 'Box zoom, matching between viewers'
    tool_tip = 'Zoom to a drawn rectangle in all viewers'


@viewer_tool
class SelectSlice(CheckableTool):
    icon = os.path.join(ICON_DIR, 'slice.svg')
    tool_id = 'jdaviz:selectslice'
    action_text = 'Select cube slice'
    tool_tip = 'Select cube slice'

    def __init__(self, viewer, **kwargs):
        self._time_last = 0
        super().__init__(viewer, **kwargs)

    def activate(self):
        self.viewer.add_event_callback(self.on_mouse_event,
                                       events=['dragmove', 'click'])
        msg = SliceToolStateMessage({'active': True}, viewer=self.viewer, sender=self)
        self.viewer.session.hub.broadcast(msg)

    def deactivate(self):
        self.viewer.remove_event_callback(self.on_mouse_event)
        msg = SliceToolStateMessage({'active': False}, viewer=self.viewer, sender=self)
        self.viewer.session.hub.broadcast(msg)

    def on_mouse_event(self, data):
        if (time.time() - self._time_last) <= 0.2:
            # throttle to 200ms
            return

        msg = SliceSelectSliceMessage(value=data['domain']['x'], sender=self)
        self.viewer.session.hub.broadcast(msg)

        self._time_last = time.time()


@viewer_tool
class SpectrumPerSpaxel(ProfileFromCube):

    icon = os.path.join(ICON_DIR, 'pixelspectra.svg')
    tool_id = 'jdaviz:spectrumperspaxel'
    action_text = 'See spectrum at a single spaxel'
    tool_tip = 'Click on the viewer and see the spectrum at that spaxel in the spectrum viewer'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._is_moving = False

    def activate(self):
        super().activate()
        for k in ("y_min", "y_max"):
            self._profile_viewer.state.add_callback(k, self.on_limits_change)

    def deactivate(self):
        for k in ("y_min", "y_max"):
            self._profile_viewer.state.remove_callback(k, self.on_limits_change)
        self.viewer.stop_stream()
        super().deactivate()

    def on_limits_change(self, *args):
        if not self._is_moving:
            self._previous_bounds = self._profile_viewer.get_limits()

    def on_mouse_move(self, data):
        if data['event'] == 'mouseleave':
            self._mark.visible = False
            self.viewer.stop_stream()
            self._reset_profile_viewer_bounds()
            self._is_moving = False
            return

        self._is_moving = True
        try:
            x = int(np.round(data['domain']['x']))
            y = int(np.round(data['domain']['y']))
            self._mouse_move_worker(x, y)
        finally:
            self._is_moving = False

    def _mouse_move_worker(self, x, y):
        # Use the selected layer from coords_info as long as it's 3D
        coords_dataset = self.viewer.session.application._tools['g-coords-info'].dataset.selected
        if coords_dataset == 'auto':
            cube_data = self.viewer.active_image_layer.layer
        elif coords_dataset == 'none':
            if len(self.viewer.layers):
                cube_data = self.viewer.layers[0].layer
            else:
                return
        else:
            cube_data = self.viewer.session.application._tools['g-coords-info'].dataset.selected_obj

        data_shape = cube_data.ndim if hasattr(cube_data, "ndim") else len(cube_data.shape)
        if data_shape != 3:
            cube_data = [layer.layer for layer in self.viewer.layers if layer.state.visible
                         and layer.layer.ndim == 3]
            if len(cube_data) == 0:
                return
            cube_data = cube_data[0]

        if isinstance(cube_data, Spectrum1D):
            spectrum = cube_data
        else:
            spectrum = cube_data.get_object(statistic=None)
        # Note: change this when Spectrum1D.with_spectral_axis is fixed.
        x_unit = self._profile_viewer.state.x_display_unit
        if spectrum.spectral_axis.unit != x_unit:
            new_spectral_axis = spectrum.spectral_axis.to(x_unit)
            spectrum = Spectrum1D(spectrum.flux, new_spectral_axis)

        if x >= spectrum.flux.shape[0] or x < 0 or y >= spectrum.flux.shape[1] or y < 0:
            self._reset_profile_viewer_bounds()
            self._mark.visible = False
            self.viewer.stop_stream()
        else:
            y_values = spectrum.flux[x, y, :].value
            if np.all(np.isnan(y_values)):
                self._mark.visible = False
                return
            self._mark.update_xy(spectrum.spectral_axis.value, y_values)
            self._mark.visible = True

            self.viewer.start_stream()
            self.viewer.update_sonified_cube(x, y)

            # Data might have inf too.
            new_ymin = np.nanmin(y_values)
            new_ymax = np.nanmax(y_values)
            if np.all(np.isfinite([new_ymin, new_ymax])):
                self._profile_viewer.set_limits(y_min=new_ymin * 0.8, y_max=new_ymax * 1.2)
