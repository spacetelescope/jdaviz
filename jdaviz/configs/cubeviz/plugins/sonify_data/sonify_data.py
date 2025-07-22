import time

from astropy.nddata import CCDData
import astropy.units as u
from astropy.wcs import WCS
import numpy as np
from scipy.special import erf
from traitlets import Bool, List, Unicode, observe

from jdaviz.core.custom_traitlets import IntHandleEmpty, FloatHandleEmpty
from jdaviz.core.registries import tray_registry
from jdaviz.core.template_mixin import (PluginTemplateMixin, DatasetSelectMixin,
                                        SpectralSubsetSelectMixin, with_spinner,
                                        AddResultsMixin)
from jdaviz.core.user_api import PluginUserApi
from jdaviz.core.events import SnackbarMessage, AddDataMessage
from jdaviz.configs.cubeviz.plugins.cube_listener import CubeListenerData, INT_MAX
from jdaviz.core.sonified_layers import SonifiedLayerState

__all__ = ['SonifyData']

try:
    import strauss  # noqa
    import sounddevice as sd
except ImportError:
    class Empty:
        pass
    sd = Empty()
    sd.default = Empty()
    sd.default.device = [-1, -1]
    _has_strauss = False
else:
    _has_strauss = True


@tray_registry('cubeviz-sonify-data', label="Sonify Data")
class SonifyData(PluginTemplateMixin, DatasetSelectMixin, SpectralSubsetSelectMixin,
                 AddResultsMixin):
    """
    See the :ref:`Sonify Data Plugin Documentation <cubeviz-sonify-data>` for more details.

    Only the following attributes and methods are available through the
    :ref:`public plugin API <plugin-apis>`:

    * :meth:`~jdaviz.core.template_mixin.PluginTemplateMixin.show`
    * :meth:`~jdaviz.core.template_mixin.PluginTemplateMixin.open_in_tray`
    * :meth:`~jdaviz.core.template_mixin.PluginTemplateMixin.close_in_tray`
    """
    template_file = __file__, "sonify_data.vue"

    # Removing UI option to vary these for now
    sample_rate = 44100  # IntHandleEmpty(44100).tag(sync=True)
    buffer_size = 2048  # IntHandleEmpty(2048).tag(sync=True)
    assidx = FloatHandleEmpty(2.5).tag(sync=True)
    ssvidx = FloatHandleEmpty(0.65).tag(sync=True)
    eln = Bool(True).tag(sync=True)
    audfrqmin = FloatHandleEmpty(50).tag(sync=True)
    audfrqmax = FloatHandleEmpty(1000).tag(sync=True)
    use_pccut = Bool(True).tag(sync=True)
    pccut = IntHandleEmpty(20).tag(sync=True)
    volume = IntHandleEmpty(100).tag(sync=True)
    stream_active = Bool(True).tag(sync=True)
    has_strauss = Bool(_has_strauss).tag(sync=True)

    # TODO: can we referesh the list, so sounddevices are up-to-date when dropdown clicked?
    sound_devices_items = List().tag(sync=True)
    sound_devices_selected = Unicode('').tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._plugin_description = 'Sonify a data cube'
        self.docs_description = 'Sonify a data cube using the Strauss package.'
        if not self.has_strauss or sd.default.device[1] < 0:
            self.disabled_msg = ('To use Sonify Data, install strauss and restart Jdaviz. You '
                                 'can do this by running pip install strauss in the command'
                                 ' line and then launching Jdaviz. Currently, this plugin only'
                                 ' works on devices with valid sound output.')

        else:
            self.sound_device_indexes = None
            self.refresh_device_list()

        self.add_results.viewer.add_filter('is_image_viewer')
        self.add_to_viewer_selected = 'flux-viewer'
        self.sonified_cube = None
        self.sonified_viewers = []
        self.sonification_wl_ranges = None
        self.sonification_wl_unit = None
        self.stream = None
        # Dictionary that contains keys with UUIDs for each
        # sonified data layer. The value of each key is another dictionary containing
        # coordinates as keys and arrays representing sounds as the value.
        self.data_lookup = {}

        self._update_label_default(None)

        self.hub.subscribe(self, AddDataMessage,
                           handler=self._data_added_to_viewer)

    @property
    def user_api(self):
        expose = ['sonify_cube']
        return PluginUserApi(self, expose)

    @observe('results_label_invalid_msg')
    def _update_label_default(self, event):
        """
        Update default label when a new sonification is added to the viewer.
        """
        # Modify default label to avoid vue error from re-using label
        self.results_label_default = self.app.return_unique_name('Sonified data', typ='data')

    def _data_added_to_viewer(self, msg):
        # Keep track of the volume attribute for each layer.
        msg.viewer.sonified_layers_enabled = []
        for layer in msg.viewer.state.layers:
            if not isinstance(layer, SonifiedLayerState):
                continue

            # Add viewer to sonified_viewers if it isn't there already
            if msg.viewer not in self.sonified_viewers:
                self.sonified_viewers.append(msg.viewer)

            # Find layer, add volume check to dictionary and add callback to volume changing and
            # audible changing
            msg.viewer.layer_volume[layer.layer.label] = layer.volume
            msg.viewer.sonified_layers_enabled += ([layer.layer.label] if
                                                   getattr(layer, 'audible', False) else [])  # noqa

            layer.remove_callback('volume', msg.viewer.recalculate_combined_sonified_grid)
            layer.remove_callback('audible', msg.viewer.recalculate_combined_sonified_grid)
            layer.add_callback('volume', msg.viewer.recalculate_combined_sonified_grid)
            layer.add_callback('audible', msg.viewer.recalculate_combined_sonified_grid)

    def start_stream(self):
        if self.stream and not self.stream.closed:
            self.stream.start()

    def stop_stream(self):
        if self.stream and not self.stream.closed:
            self.stream.stop()

    def sonify_cube(self):
        """
        Create a sonified grid in the flux viewer so that sound plays when mousing over the viewer.
        You can select the device index for audio output and also use a spectral subset to set a
        range for sonification.
        """
        t0 = time.time()
        if self.disabled_msg:
            raise ValueError('Unable to sonify cube')

        # Get index of selected device
        selected_device_index = self.sound_device_indexes[self.sound_devices_selected]

        # Apply spectral subset bounds
        if self.spectral_subset_selected != self.spectral_subset.default_text:
            display_unit = self.spectrum_viewer.state.x_display_unit
            min_wavelength = self.spectral_subset.selected_obj.lower.to_value(u.Unit(display_unit))
            max_wavelength = self.spectral_subset.selected_obj.upper.to_value(u.Unit(display_unit))
            self.sonification_wl_ranges = ([min_wavelength, max_wavelength],)
            self.sonification_wl_unit = display_unit

        # Ensure the current spectral region bounds are up-to-date at render time
        self.update_wavelength_range(None)

        previous_label = self.results_label

        # generate the sonified cube
        sonified_cube = self.get_sonified_cube(self.sample_rate, self.buffer_size,
                                               selected_device_index, self.assidx,
                                               self.ssvidx, self.pccut, self.audfrqmin,
                                               self.audfrqmax, self.eln,
                                               self.use_pccut, self.results_label)
        sonified_cube.meta['Sonified'] = True

        # For now, this still initially adds the sonified data to flux-viewer
        self.add_results.add_results_from_plugin(sonified_cube, replace=False)
        self.add_results.viewer.selected_obj.recalculate_combined_sonified_grid()

        t1 = time.time()
        msg = SnackbarMessage(f"'{previous_label}' sonified successfully in {t1-t0} seconds.",
                              color='success',
                              sender=self)
        self.app.hub.broadcast(msg)

    def get_sonified_cube(self, sample_rate, buffer_size, device, assidx, ssvidx,
                          pccut, audfrqmin, audfrqmax, eln, use_pccut, results_label):
        spectrum = self.dataset.selected_obj
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
                                              eln=eln, vol=self.volume,
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

        # Attempt to copy the spatial WCS information from the cube
        if hasattr(spectrum.wcs, 'celestial'):
            wcs = spectrum.wcs.celestial
        elif hasattr(spectrum.wcs, 'to_fits_sip'):
            # GWCS case
            wcs = WCS(spectrum.wcs.to_fits_sip())
        else:
            wcs = None

        sonified_cube = CCDData(a * u.Unit(''), wcs=wcs)
        return sonified_cube

    def update_sonified_cube_with_coord(self, viewer, coord, vollim='buff'):
        # Set newsig to the combined sound array at coord
        if (int(coord[0]), int(coord[1])) not in viewer.combined_sonified_grid:
            return

        # use cached version of combined sonified grid
        compsig = viewer.combined_sonified_grid[int(coord[0]), int(coord[1])]

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

    @with_spinner()
    def vue_sonify_cube(self, *args):
        self.sonify_cube()

    def vue_start_stop_stream(self, *args):
        self.stream_active = not self.stream_active

    @observe('spectral_subset_selected')
    def update_wavelength_range(self, event):
        if not hasattr(self, 'spectral_subset'):
            return
        display_unit = self.spectrum_viewer.state.x_display_unit
        # is this spectral selection or the entire spectrum?
        if hasattr(self.spectral_subset.selected_obj, "subregions"):
            wlranges = self.spectral_subset.selected_obj.subregions
        else:
            wlranges = None
        self.sonification_wl_ranges = wlranges
        self.sonification_wl_unit = display_unit

    @observe('volume')
    def update_volume_level(self, event):
        for viewer in self.sonified_viewers:
            viewer.update_volume_level(event['new'])

    @observe('sound_devices_selected')
    def update_sound_device(self, event):
        # This might get called before the plugin is fully initialized
        if not hasattr(self, 'sonified_cube') or not self.sonified_cube:
            return
        if event['new'] != event['old']:
            didx = dict(zip(*self.build_device_lists()))[event['new']]
            # This was moved here from viewers.py now that the stream is handled here.
            self.stop_stream()
            self.stream = sd.OutputStream(samplerate=self.sample_rate, blocksize=self.buffer_size,
                                          device=didx, channels=1, dtype='int16', latency='low',
                                          callback=self.sonified_cube.player_callback)

    def refresh_device_list(self):
        devices, indexes = self.build_device_lists()
        self.sound_device_indexes = dict(zip(devices, indexes))
        self.sound_devices_items = devices
        self.sound_devices_selected = dict(zip(indexes, devices))[sd.default.device[1]]

    def vue_refresh_device_list_in_dropdown(self, *args):
        self.refresh_device_list()

    def build_device_lists(self):
        # dedicated function to build the current *output*
        # device and index lists
        devices = []
        device_indexes = []
        for index, device in enumerate(sd.query_devices()):
            if device['max_output_channels'] > 0 and device['name'] not in devices:
                devices.append(device['name'])
                device_indexes.append(index)
        return devices, device_indexes
