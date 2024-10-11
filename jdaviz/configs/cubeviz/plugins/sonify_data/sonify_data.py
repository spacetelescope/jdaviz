import sounddevice as sd

from echo import delay_callback
from traitlets import Bool, List, Unicode, observe

from jdaviz.core.custom_traitlets import IntHandleEmpty, FloatHandleEmpty
from jdaviz.core.registries import tray_registry
from jdaviz.core.template_mixin import PluginTemplateMixin, DatasetSelectMixin, with_spinner


__all__ = ['SonifyData']


@tray_registry('cubeviz-sonify-data', label="Sonify Data",
               viewer_requirements=['spectrum', 'image'])
class SonifyData(PluginTemplateMixin, DatasetSelectMixin):
    template_file = __file__, "sonify_data.vue"

    sample_rate = IntHandleEmpty(44100).tag(sync=True)
    buffer_size = IntHandleEmpty(2048).tag(sync=True)
    assidx = FloatHandleEmpty(2.5).tag(sync=True)
    ssvidx = FloatHandleEmpty(0.65).tag(sync=True)
    eln = Bool(False).tag(sync=True)
    wavemin = FloatHandleEmpty().tag(sync=True)
    wavemax = FloatHandleEmpty().tag(sync=True)
    audfrqmin = FloatHandleEmpty(50).tag(sync=True)
    audfrqmax = FloatHandleEmpty(1500).tag(sync=True)
    pccut = IntHandleEmpty(20).tag(sync=True)
    volume = IntHandleEmpty(100).tag(sync=True)

    sound_devices_items = List().tag(sync=True)
    sound_devices_selected = Unicode('').tag(sync=True)
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.sound_devices_items = [device['name'] for device in sd.query_devices()]
        self.sound_devices_selected = self.sound_devices_items[sd.default.device[1]]

        # TODO: Remove hardcoded range viewer
        self.spec_viewer = self.app.get_viewer('spectrum-viewer')
        self.spec_viewer.state.add_callback("x_min", self._update_x_values)
        self.spec_viewer.state.add_callback("x_max", self._update_x_values)

    @with_spinner()
    def vue_sonify_cube(self, *args):
        viewer = self.app.get_viewer('flux-viewer')
        # Get index of selected device since name may not be unique
        selected_device_index = self.sound_devices_items.index(self.sound_devices_selected)
        viewer.get_sonified_cube(self.sample_rate, self.buffer_size, selected_device_index,
                                 self.assidx, self.ssvidx, self.pccut, self.audfrqmin,
                                 self.audfrqmax, self.eln)

        # Automatically select spectrum-at-spaxel tool
        viewer.toolbar.active_tool = viewer.toolbar.tools['jdaviz:spectrumperspaxel']

    def _update_x_values(self, event):
        with delay_callback(self.spec_viewer.state, 'x_min', 'x_max'):
            self.wavemin, self.wavemax = self.spec_viewer.state.x_min, self.spec_viewer.state.x_max

    @observe('wavemin', 'wavemax')
    def update_viewer_range(self, event):
        with delay_callback(self.spec_viewer.state, 'x_min', 'x_max'):
            self.spec_viewer.state.x_min, self.spec_viewer.state.x_max = self.wavemin, self.wavemax
