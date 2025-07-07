from functools import cached_property

from glue.core import BaseData

from glue_jupyter.bqplot.image import BqplotImageView
import numpy as np
from astropy import units as u
from astropy.nddata import CCDData
from astropy.wcs import WCS
from scipy.special import erf

from jdaviz.core.registries import viewer_registry
from jdaviz.configs.cubeviz.plugins.mixins import WithSliceIndicator, WithSliceSelection
from jdaviz.configs.default.plugins.viewers import JdavizViewerMixin
from jdaviz.configs.specviz.plugins.viewers import Spectrum1DViewer
from jdaviz.core.freezable_state import FreezableBqplotImageViewerState
from jdaviz.configs.cubeviz.plugins.cube_listener import CubeListenerData, MINVOL, INT_MAX
from jdaviz.core.sonified_layers import (SonifiedDataLayerArtist,
                                         SonifiedLayerStateWidget,
                                         SonifiedLayerState)


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

        self.add_event_callback(self._viewer_mouse_event, events=['mousemove',
                                                                  'mouseleave',
                                                                  'mouseenter'])

        # Hide axes by default
        self.state.show_axes = False

        self.sonified_cube = None
        self.stream = None

        self.sonification_wl_ranges = None
        self.sonification_wl_unit = None
        self.volume_level = None

        self.data_menu._obj.dataset.add_filter('is_cube_or_image')

        # Dictionary that contains keys with UUIDs for each
        # sonified data layer. The value of each key is another dictionary containing
        # coordinates as keys and arrays representing sounds as the value.
        self.data_lookup = {}
        self.layer_volume = {}
        self.sonified_layers_enabled = []
        self.same_pix = None
        self._cached_properties = ['combined_sonified_grid']

        self._layer_style_widget_cls[SonifiedDataLayerArtist] = SonifiedLayerStateWidget

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
        if self.stream and not self.stream.closed:
            self.stream.start()

    def stop_stream(self):
        if self.stream and not self.stream.closed:
            self.stream.stop()

    def recalculate_combined_sonified_grid(self, event=None):
        self.layer_volume = {}
        self.sonified_layers_enabled = []
        # Keep track of the volume attribute for each layer.
        for layer in self.state.layers:
            if not isinstance(layer, SonifiedLayerState):
                continue

            # Find layer, add volume check to dictionary and add callback to volume changing and
            # audible changing
            self.layer_volume[layer.layer.label] = layer.volume
            self.sonified_layers_enabled += ([layer.layer.label] if
                                             getattr(layer, 'audible', False) else [])

            # TODO: is there a better way to ensure that only unique callbacks are added?
            layer.remove_callback('volume', self.recalculate_combined_sonified_grid)
            layer.remove_callback('audible', self.recalculate_combined_sonified_grid)

            layer.add_callback('volume', self.recalculate_combined_sonified_grid)
            layer.add_callback('audible', self.recalculate_combined_sonified_grid)

        # Need to force an update of the layer icons since
        # audible is a state attribute, not a layer artist attribute
        self.jdaviz_app.state.layer_icons.notify_all()

        if 'combined_sonified_grid' in self.__dict__:
            del self.__dict__['combined_sonified_grid']
        self.combined_sonified_grid

    @cached_property
    def combined_sonified_grid(self):
        if not self.sonified_layers_enabled:
            self.stop_stream()
            return {}

        compiled_coords = {}
        for k, v in self.data_lookup.items():
            if k not in self.sonified_layers_enabled:
                continue
            # Each (x, y) coordinate corresponds to a different sound for each layer.
            # These sounds can be combined together and played by setting cbuff to True.
            # TODO: is there a better way to combine sounds or normalize them?
            # TODO: apply 1/N or 1/N**0.5 normalisation per layer for N layers?
            for coord, sound_array in v.items():
                if coord in compiled_coords:
                    compiled_coords[coord] += ((sound_array * (int(self.layer_volume[k]) / 100)).
                                               astype(int))
                else:
                    compiled_coords[coord] = ((sound_array * (int(self.layer_volume[k]) / 100)).
                                              astype(int))
        return compiled_coords

    def update_sonified_cube_with_coord(self, coord, vollim='buff'):
        # Set newsig to the combined sound array at coord
        if (not self.sonified_layers_enabled or
                (int(coord[0]), int(coord[1])) not in self.combined_sonified_grid):
            return

        # use cached version of combined sonified grid
        compsig = self.combined_sonified_grid[int(coord[0]), int(coord[1])]

        # Adjust volume to remove clipping
        if vollim == 'sig':
            # sigmoidal volume limiting
            self.sonified_cube.newsig = (erf(compsig/INT_MAX) * INT_MAX).astype('int16')
        elif vollim == 'clip':
            # hard-clipped volume limiting
            self.sonified_cube.newsig = np.clip(compsig, -INT_MAX, INT_MAX).astype('int16')
        elif vollim == 'buff':
            # renormalise buffer
            sigmax = abs(compsig).max()
            if sigmax > INT_MAX:
                compsig = ((INT_MAX/abs(compsig).max()) * compsig)
            self.sonified_cube.newsig = compsig.astype('int16')
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
                          pccut, audfrqmin, audfrqmax, eln, use_pccut, results_label):
        spectrum = self.active_cube_layer.layer.get_object(statistic=None)
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
            flux_slices = [slice(None),]*3
            flux_slices[spectrum.spectral_axis_index] = wdx
            flux = flux[*flux_slices]

        pc_cube = np.percentile(np.nan_to_num(flux), np.clip(pccut, 0, 99),
                                axis=spectrum.spectral_axis_index)

        # clip zeros and remove NaNs
        clipped_arr = np.nan_to_num(np.clip(flux, 0, np.inf), copy=False)

        # make a rough white-light image from the clipped array
        whitelight = np.expand_dims(clipped_arr.sum(spectrum.spectral_axis_index),
                                    axis=spectrum.spectral_axis_index)

        if use_pccut:
            # subtract any percentile cut
            clipped_arr -= np.expand_dims(pc_cube, axis=spectrum.spectral_axis_index)

            # and re-clip
            clipped_arr = np.clip(clipped_arr, 0, np.inf)

        self.sonified_cube = CubeListenerData(clipped_arr ** assidx, wlens, duration=0.8,
                                              samplerate=sample_rate, buffsize=buffer_size,
                                              wl_unit=self.sonification_wl_unit,
                                              audfrqmin=audfrqmin, audfrqmax=audfrqmax,
                                              eln=eln, vol=self.volume_level,
                                              spectral_axis_index=spectrum.spectral_axis_index)
        self.sonified_cube.sonify_cube()
        self.sonified_cube.sigcube = (
                self.sonified_cube.sigcube * pow(whitelight / whitelight.max(),
                                                 ssvidx)).astype('int16')
        self.stream = sd.OutputStream(samplerate=sample_rate, blocksize=buffer_size, device=device,
                                      channels=1, dtype='int16', latency='low',
                                      callback=self.sonified_cube.player_callback)
        self.sonified_cube.cbuff = True

        spatial_inds = [0, 1, 2]
        spatial_inds.remove(spectrum.spectral_axis_index)
        x_size = self.sonified_cube.sigcube.shape[spatial_inds[0]]
        y_size = self.sonified_cube.sigcube.shape[spatial_inds[1]]

        # Create a new entry for the sonified layer in data_lookup. The value is a dictionary
        # containing (x_size * y_size) keys with values being arrays that represent sounds
        if spectrum.spectral_axis_index == 2:
            self.data_lookup[results_label] = {(x, y): self.sonified_cube.sigcube[x, y, :]
                                               for x in range(0, x_size)
                                               for y in range(0, y_size)}
        elif spectrum.spectral_axis_index == 0:
            # This looks wrong but it's because in this case x_size is actually the y axis and vice
            # versa, wasn't sure about the best way to handle the spatial_inds thing above.
            self.data_lookup[results_label] = {(y, x): self.sonified_cube.sigcube[:, x, y]
                                               for x in range(0, x_size)
                                               for y in range(0, y_size)}

        # Create a 2D array with coordinates starting at (0, 0) and going until (x_size, y_size)
        a = np.arange(1, x_size * y_size + 1).reshape((x_size, y_size))

        if hasattr(spectrum.wcs, 'celestial'):
            wcs = spectrum.wcs.celestial
        elif hasattr(spectrum.wcs, 'to_fits_sip'):
            # GWCS case
            wcs = WCS(spectrum.wcs.to_fits_sip())
        else:
            wcs = None

        # Create add data with name results_label to data collection and then add it to the
        # flux viewer
        sonified_cube = CCDData(a * u.Unit(''), wcs=wcs)
        return sonified_cube

    def _viewer_mouse_event(self, data):
        if data['event'] in ('mouseleave', 'mouseenter') or not self.sonified_layers_enabled:
            self.stop_stream()
            return
        if len(self.jdaviz_app.data_collection) < 1:
            return

        # Extract data coordinates - these are pixels in the reference image
        x = np.floor(data['domain']['x'])
        y = np.floor(data['domain']['y'])

        if x is None or y is None or x < 0 or y < 0:  # Out of bounds
            return

        if self.same_pix is None:
            self.same_pix = (x, y)
        elif (x, y) == self.same_pix:
            return

        if (not self.sonified_cube or not hasattr(self.sonified_cube, 'newsig') or
                not hasattr(self.sonified_cube, 'sigcube')):
            return
        self.start_stream()
        self.update_sonified_cube_with_coord((x, y))

    def get_data_layer_artist(self, layer=None, layer_state=None):
        if 'Sonified' in layer.meta:
            cls = SonifiedDataLayerArtist
            return self.get_layer_artist(cls, layer=layer)
        else:
            return super().get_data_layer_artist(layer, layer_state)


@viewer_registry("cubeviz-profile-viewer", label="Profile 1D (Cubeviz)")
class CubevizProfileView(Spectrum1DViewer, WithSliceIndicator):
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

    def add_subset(self, subset, *args, **kwargs):
        # The cubeviz profile viewer does not show the spectra/profiles based
        # on the subsets of the cubes, but based on extracted datasets derived
        # from those subsets. We can ignore all subsets that have a subset
        # state that was defined from the image, and we recognize these by
        # looking for subset states that are defined based on two attributes.
        if len(subset.subset_state.attributes) == 2:
            return False
        else:
            return super().add_subset(subset, *args, **kwargs)
