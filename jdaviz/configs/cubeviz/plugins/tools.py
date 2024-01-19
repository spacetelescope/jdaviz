import time
import os

from glue.config import viewer_tool
from glue_jupyter.bqplot.image import BqplotImageView
from glue_jupyter.bqplot.image.layer_artist import BqplotImageSubsetLayerArtist
from glue.viewers.common.tool import CheckableTool
import numpy as np
from specutils import Spectrum1D

from jdaviz.configs.imviz.plugins.tools import _MatchedZoomMixin
from jdaviz.core.events import SliceToolStateMessage
from jdaviz.core.tools import PanZoom, BoxZoom, SinglePixelRegion
from jdaviz.core.marks import PluginLine

__all__ = []

ICON_DIR = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'data', 'icons')


class _PixelMatchedZoomMixin(_MatchedZoomMixin):
    match_keys = ('x_min', 'x_max', 'y_min', 'y_max')
    disable_matched_zoom_in_other_viewer = False

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
    action_text = 'Select cube slice (spectral axis)'
    tool_tip = 'Select cube slice (spectral axis)'

    def __init__(self, viewer, **kwargs):
        self._time_last = 0
        super().__init__(viewer, **kwargs)

    def activate(self):
        self.viewer.add_event_callback(self.on_mouse_event,
                                       events=['dragmove', 'click'])
        msg = SliceToolStateMessage({'active': True}, sender=self)
        self.viewer.session.hub.broadcast(msg)

    def deactivate(self):
        self.viewer.remove_event_callback(self.on_mouse_event)
        msg = SliceToolStateMessage({'active': False}, sender=self)
        self.viewer.session.hub.broadcast(msg)

    def on_mouse_event(self, data):
        if (time.time() - self._time_last) <= 0.2:
            # throttle to 200ms
            return

        self.viewer.jdaviz_helper.select_wavelength(data['domain']['x'])

        self._time_last = time.time()


@viewer_tool
class SpectrumPerSpaxel(SinglePixelRegion):

    icon = os.path.join(ICON_DIR, 'pixelspectra.svg')
    tool_id = 'jdaviz:spectrumperspaxel'
    action_text = 'See spectrum at a single spaxel'
    tool_tip = 'Click on the viewer and see the spectrum at that spaxel in the spectrum viewer'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._spectrum_viewer = None
        self._previous_bounds = None
        self._mark = None
        self._data = None

    def _reset_spectrum_viewer_bounds(self):
        sv_state = self._spectrum_viewer.state
        sv_state.x_min = self._previous_bounds[0]
        sv_state.x_max = self._previous_bounds[1]
        sv_state.y_min = self._previous_bounds[2]
        sv_state.y_max = self._previous_bounds[3]

    def activate(self):
        self.viewer.add_event_callback(self.on_mouse_move, events=['mousemove', 'mouseleave'])
        if self._spectrum_viewer is None:
            self._spectrum_viewer = self.viewer.jdaviz_helper.app.get_viewer('spectrum-viewer')
        if self._mark is None:
            self._mark = PluginLine(self._spectrum_viewer, visible=False)
            self._spectrum_viewer.figure.marks = self._spectrum_viewer.figure.marks + [self._mark,]
        # Store these so we can revert to previous user-set zoom after preview view
        sv_state = self._spectrum_viewer.state
        self._previous_bounds = [sv_state.x_min, sv_state.x_max, sv_state.y_min, sv_state.y_max]
        super().activate()

    def deactivate(self):
        self.viewer.remove_event_callback(self.on_mouse_move)
        self._reset_spectrum_viewer_bounds()
        super().deactivate()

    def on_mouse_move(self, data):
        if data['event'] == 'mouseleave':
            self._mark.visible = False
            self._reset_spectrum_viewer_bounds()
            return

        x = int(np.round(data['domain']['x']))
        y = int(np.round(data['domain']['y']))

        # Use the selected layer from coords_info as long as it's 3D
        coords_info_dataset = self.viewer.session.application._tools['g-coords-info'].dataset.selected
        if coords_info_dataset == 'auto':
            cube_data = self.viewer.active_image_layer.layer
        elif coords_info_dataset == 'none':
            cube_data = self.viewer.layers[0].layer
        else:
            for layer in self.viewer.layers:
                if layer.layer.label == coords_info_dataset and layer.visible:
                    if isinstance(layer, BqplotImageSubsetLayerArtist):
                        # cannot expose info for spatial subset layers
                        continue
                    cube_data = layer.layer
                    break
            else:
                return

        if cube_data.ndim != 3:
            cube_data = [layer.layer for layer in self.viewer.layers if layer.state.visible
                        and layer.layer.ndim == 3]
            if len(cube_data) == 0:
                return
            cube_data = cube_data[0]

        spectrum = cube_data.get_object(statistic=None)
        # Note: change this when Spectrum1D.with_spectral_axis is fixed.
        if spectrum.spectral_axis.unit != self._spectrum_viewer.state.x_display_unit:
            new_spectral_axis = spectrum.spectral_axis.to(self._spectrum_viewer.state.x_display_unit)
            spectrum = Spectrum1D(spectrum.flux, new_spectral_axis)

        if x >= spectrum.flux.shape[0] or x < 0 or y >= spectrum.flux.shape[1] or y < 0:
            self._reset_spectrum_viewer_bounds()
            self._mark.visible = False
        else:
            y_values = spectrum.flux[x, y, :]
            if np.all(np.isnan(y_values)):
                self._mark.visible = False
                return
            self._mark.update_xy(spectrum.spectral_axis.value, y_values)
            self._mark.visible = True
            self._spectrum_viewer.state.y_max = np.nanmax(y_values.value) * 1.2
            self._spectrum_viewer.state.y_min = np.nanmin(y_values.value) * 0.8
