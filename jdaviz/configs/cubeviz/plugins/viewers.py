from glue.core import BaseData
from glue_jupyter.bqplot.image import BqplotImageView

from jdaviz.core.registries import viewer_registry
from jdaviz.configs.cubeviz.plugins.mixins import WithSliceIndicator, WithSliceSelection
from jdaviz.configs.default.plugins.viewers import JdavizViewerMixin
from jdaviz.configs.specviz.plugins.viewers import SpecvizProfileView
from jdaviz.core.freezable_state import FreezableBqplotImageViewerState
from jdaviz.configs.cubeviz.plugins.cube_listener import CubeListenerData, MINVOL
import numpy as np
from astropy import units as u

try:
    import sounddevice as sd
except ImportError:
    pass

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
        self.state._set_viewer(self)

        self._subscribe_to_layers_update()
        self.state.add_callback('reference_data', self._initial_x_axis)

        # Hide axes by default
        self.state.show_axes = False

        self.sonified_cube = None
        self.stream = None

        self.sonification_wl_ranges = None
        self.sonification_wl_unit = None
        self.volume_level = None
        self.stream_active = True

        self.data_menu._obj.dataset.add_filter('is_cube_or_image')

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

    def update_sonified_cube(self, x, y):
        if (not self.sonified_cube or not hasattr(self.sonified_cube, 'newsig') or
                not hasattr(self.sonified_cube, 'sigcube')):
            return
        self.sonified_cube.newsig = self.sonified_cube.sigcube[x, y, :]
        self.sonified_cube.cbuff = True

    def update_listener_wls(self, wranges, wunit):
        self.sonification_wl_ranges = wranges
        self.sonification_wl_unit = wunit

    def update_sound_device(self, device_index):
        if not self.sonified_cube:
            return

        self.stop_stream()
        self.stream = sd.OutputStream(samplerate=self.sample_rate, blocksize=self.buffer_size,
                                      device=device_index, channels=1, dtype='int16',
                                      latency='low', callback=self.sonified_cube.player_callback)

    def update_volume_level(self, level):
        if not self.sonified_cube:
            return
        self.volume_level = level
        self.sonified_cube.atten_level = int(1/np.clip((level/100.)**2, MINVOL, 1))

    def get_sonified_cube(self, sample_rate, buffer_size, device, assidx, ssvidx,
                          pccut, audfrqmin, audfrqmax, eln, use_pccut):
        spectrum = self.active_image_layer.layer.get_object(statistic=None)
        wlens = spectrum.wavelength.to('m').value
        flux = spectrum.flux.value
        self.sample_rate = sample_rate
        self.buffer_size = buffer_size

        if self.sonification_wl_ranges:
            wdx = np.zeros(wlens.size).astype(bool)
            for r in self.sonification_wl_ranges:
                # index just the spectral subregion
                wdx = np.logical_or(wdx,
                                    np.logical_and(wlens >= r[0].to_value(u.m),
                                                   wlens <= r[1].to_value(u.m)))
            wlens = wlens[wdx]
            flux = flux[:, :, wdx]

        pc_cube = np.percentile(np.nan_to_num(flux), np.clip(pccut, 0, 99), axis=-1)

        # clip zeros and remove NaNs
        clipped_arr = np.nan_to_num(np.clip(flux, 0, np.inf), copy=False)

        # make a rough white-light image from the clipped array
        whitelight = np.expand_dims(clipped_arr.sum(-1), axis=2)

        if use_pccut:
            # subtract any percentile cut
            clipped_arr -= np.expand_dims(pc_cube, axis=2)

            # and re-clip
            clipped_arr = np.clip(clipped_arr, 0, np.inf)

        self.sonified_cube = CubeListenerData(clipped_arr ** assidx, wlens, duration=0.8,
                                              samplerate=sample_rate, buffsize=buffer_size,
                                              wl_unit=self.sonification_wl_unit,
                                              audfrqmin=audfrqmin, audfrqmax=audfrqmax,
                                              eln=eln, vol=self.volume_level)
        self.sonified_cube.sonify_cube()
        self.sonified_cube.sigcube = (
                self.sonified_cube.sigcube * pow(whitelight / whitelight.max(),
                                                 ssvidx)).astype('int16')
        self.stream = sd.OutputStream(samplerate=sample_rate, blocksize=buffer_size, device=device,
                                      channels=1, dtype='int16', latency='low',
                                      callback=self.sonified_cube.player_callback)
        self.sonified_cube.cbuff = True


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
