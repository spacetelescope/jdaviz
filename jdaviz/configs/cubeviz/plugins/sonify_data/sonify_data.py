import time
from traitlets import Bool, List, Unicode, observe
import astropy.units as u

from jdaviz.core.custom_traitlets import IntHandleEmpty, FloatHandleEmpty
from jdaviz.core.registries import tray_registry
from jdaviz.core.template_mixin import (PluginTemplateMixin, DatasetSelectMixin,
                                        SpectralSubsetSelectMixin, with_spinner,
                                        AddResultsMixin)
from jdaviz.core.user_api import PluginUserApi
from jdaviz.core.events import SnackbarMessage


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

    add_to_viewer_enabled = Bool(False).tag(sync=True)

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

        self.add_to_viewer_selected = 'flux-viewer'

        self._update_label_default(None)

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
            self.flux_viewer.update_listener_wls((min_wavelength, max_wavelength), display_unit)

        # Ensure the current spectral region bounds are up-to-date at render time
        self.update_wavelength_range(None)

        previous_label = self.results_label

        # generate the sonified cube
        sonified_cube = self.flux_viewer.get_sonified_cube(self.sample_rate, self.buffer_size,
                                                           selected_device_index, self.assidx,
                                                           self.ssvidx, self.pccut, self.audfrqmin,
                                                           self.audfrqmax, self.eln,
                                                           self.use_pccut, self.results_label)
        sonified_cube.meta['Sonified'] = True
        self.add_results.add_results_from_plugin(sonified_cube, replace=False)

        self.flux_viewer.recalculate_combined_sonified_grid()

        t1 = time.time()
        msg = SnackbarMessage(f"'{previous_label}' sonified successfully in {t1-t0} seconds.",
                              color='success',
                              sender=self)
        self.app.hub.broadcast(msg)

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
        self.flux_viewer.update_listener_wls(wlranges, display_unit)

    @observe('volume')
    def update_volume_level(self, event):
        self.flux_viewer.update_volume_level(event['new'])

    @observe('sound_devices_selected')
    def update_sound_device(self, event):
        if event['new'] != event['old']:
            didx = dict(zip(*self.build_device_lists()))[event['new']]
            self.flux_viewer.update_sound_device(didx)

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
