from glue.core import BaseData
from glue_jupyter.bqplot.image import BqplotImageView

from jdaviz.core.registries import viewer_registry
from jdaviz.configs.cubeviz.plugins.mixins import WithSliceIndicator, WithSliceSelection
from jdaviz.configs.default.plugins.viewers import JdavizViewerMixin
from jdaviz.configs.specviz.plugins.viewers import SpecvizProfileView
from jdaviz.core.freezable_state import FreezableBqplotImageViewerState
from jdaviz.configs.cubeviz.plugins.cube_listener import CubeListenerData
import numpy as np
import sounddevice as sd
from astropy import units as u

__all__ = ['CubevizImageView', 'CubevizProfileView']

@viewer_registry("cubeviz-image-viewer", label="Image 2D (Cubeviz)")
class CubevizImageView(JdavizViewerMixin, WithSliceSelection, BqplotImageView):
    # categories: zoom resets, (zoom, pan), subset, select tools, shortcuts
    # NOTE: zoom and pan are merged here for space consideration and to avoid
    # overflow to second row when opening the tray
    tools_nested = [
                    ['jdaviz:homezoom', 'jdaviz:prevzoom'],
                    ['jdaviz:pixelboxzoommatch', 'jdaviz:boxzoom',
                     'jdaviz:pixelpanzoommatch', 'jdaviz:panzoom'],
                    ['bqplot:truecircle', 'bqplot:rectangle', 'bqplot:ellipse',
                     'bqplot:circannulus'],
                    ['jdaviz:spectrumperspaxel'],
                    ['jdaviz:sidebar_plot', 'jdaviz:sidebar_export']
                ]

    default_class = None
    _state_cls = FreezableBqplotImageViewerState

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # provide reference from state back to viewer to use for zoom syncing
        self.state._viewer = self

        self._subscribe_to_layers_update()
        self.state.add_callback('reference_data', self._initial_x_axis)

        # Hide axes by default
        self.state.show_axes = False

        self.audified_cube = None
        self.stream = None
        self.audification_wl_bounds = None
        self.audification_wl_unit = None
        self.volume_level = None
        self.stream_active = True
        
    @property
    def _default_spectrum_viewer_reference_name(self):
        return self.jdaviz_helper._default_spectrum_viewer_reference_name

    @property
    def _default_flux_viewer_reference_name(self):
        return self.jdaviz_helper._default_flux_viewer_reference_name

    @property
    def _default_uncert_viewer_reference_name(self):
        return self.jdaviz_helper._default_uncert_viewer_reference_name

    def _initial_x_axis(self, *args):
        # Make sure that the x_att is correct on data load
        ref_data = self.state.reference_data
        if ref_data and ref_data.ndim == 3:
            for att_name in ["Right Ascension", "RA", "Galactic Longitude"]:
                if att_name in ref_data.component_ids():
                    x_att = att_name
                    self.state.x_att_world = ref_data.id[x_att]
                    break
            else:
                x_att = "Pixel Axis 0 [z]"
                self.state.x_att = ref_data.id[x_att]

    def set_plot_axes(self):
        self.figure.axes[1].tick_format = None
        self.figure.axes[0].tick_format = None

        self.figure.axes[1].label = "y: pixels"
        self.figure.axes[0].label = "x: pixels"

        # Make it so y axis label is not covering tick numbers.
        self.figure.axes[1].label_offset = "-50"

    def data(self, cls=None):
        return [layer_state.layer  # .get_object(cls=cls or self.default_class)
                for layer_state in self.state.layers
                if hasattr(layer_state, 'layer') and
                isinstance(layer_state.layer, BaseData)]

    def start_stream(self):
        if self.stream and not self.stream.closed and self.stream_active:
            self.stream.start()

    def stop_stream(self):
        if self.stream and not self.stream.closed and self.stream_active:
            self.stream.stop()

    def update_cube(self, x, y):
        if not self.audified_cube or not hasattr(self.audified_cube, 'newsig') or not hasattr(self.audified_cube, 'sigcube'):
            return
        self.audified_cube.newsig = self.audified_cube.sigcube[x, y, :]
        self.audified_cube.cbuff = True

    def update_listener_wl_bounds(self, w1,w2):
        if not self.audified_cube:
            return
        self.audified_cube.set_wl_bounds(w1, w2)

    def update_sound_device(self, device_index):
        # TODO: Use volume attribute for sonified cube
        if not self.audified_cube:
            return

        self.stop_stream()
        self.stream = sd.OutputStream(samplerate=self.sample_rate, blocksize=self.buffer_size,
                                      device=device_index, channels=1, dtype='int16',
                                      latency='low', callback=self.audified_cube.player_callback)

    def update_volume_level(self, level):
        # TODO: Use volume attribute for sonified cube
        if not self.audified_cube:
            return
        self.volume_level = level
        self.audified_cube.atten_level = int(np.clip((100/level)**2, 0, 2**15-1))

    def get_sonified_cube(self, sample_rate, buffer_size, device, assidx, ssvidx,
                          pccut, audfrqmin, audfrqmax, eln):
        spectrum = self.active_image_layer.layer.get_object(statistic=None)       
        wlens = spectrum.wavelength.to('m').value
        flux = spectrum.flux.value
        self.sample_rate = sample_rate
        self.buffer_size = buffer_size
        
        if self.audification_wl_bounds:
            wl_unit = getattr(u, self.audification_wl_unit)
            si_wl_bounds = (self.audification_wl_bounds * wl_unit).to('m')
            wdx = np.logical_and(wlens >= si_wl_bounds[0].value,
                                 wlens <= si_wl_bounds[1].value)
            wlens = wlens[wdx]
            flux = flux[:, :, wdx]
            
        pc_cube = np.percentile(np.nan_to_num(flux), np.clip(pccut, 0, 99), axis=-1)

        # clip zeros and remove NaNs
        clipped_arr = np.nan_to_num(np.clip(flux, 0, np.inf), copy=False)

        # make a rough white-light image from the clipped array
        whitelight = np.expand_dims(clipped_arr.sum(-1), axis=2)

        # subtract any percentile cut
        clipped_arr -= np.expand_dims(pc_cube, axis=2)

        # and re-clip
        clipped_arr = np.clip(clipped_arr, 0, np.inf)

        print(f"making cube with {self.audification_wl_bounds}")
        self.audified_cube = CubeListenerData(clipped_arr ** assidx, wlens, duration=0.8,
                                              samplerate=sample_rate, buffsize=buffer_size,
                                              wl_bounds=self.audification_wl_bounds,
                                              wl_unit=self.audification_wl_unit,
                                              audfrqmin=audfrqmin, audfrqmax=audfrqmax,
                                              eln=eln, vol=self.volume_level)
        self.audified_cube.audify_cube()
        self.audified_cube.sigcube = (
                self.audified_cube.sigcube * pow(whitelight / whitelight.max(),
                                                 ssvidx)).astype('int16')
        self.stream = sd.OutputStream(samplerate=sample_rate, blocksize=buffer_size, device=device,
                                      channels=1, dtype='int16', latency='low',
                                      callback=self.audified_cube.player_callback)
        print(sd.query_devices(), device)
        self.audified_cube.cbuff = True


@viewer_registry("cubeviz-profile-viewer", label="Profile 1D (Cubeviz)")
class CubevizProfileView(SpecvizProfileView, WithSliceIndicator):
    # categories: zoom resets, zoom, pan, subset, select tools, shortcuts
    tools_nested = [
                    ['jdaviz:homezoom', 'jdaviz:prevzoom'],
                    ['jdaviz:boxzoom', 'jdaviz:xrangezoom', 'jdaviz:yrangezoom'],
                    ['jdaviz:panzoom', 'jdaviz:panzoom_x', 'jdaviz:panzoom_y'],
                    ['bqplot:xrange'],
                    ['jdaviz:selectslice', 'jdaviz:selectline'],
                    ['jdaviz:sidebar_plot', 'jdaviz:sidebar_export']
                ]

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('default_tool_priority', ['jdaviz:selectslice'])
        super().__init__(*args, **kwargs)

    @property
    def _default_flux_viewer_reference_name(self):
        return self.jdaviz_helper._default_flux_viewer_reference_name
