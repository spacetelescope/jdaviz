from jdaviz.core.custom_traitlets import IntHandleEmpty, FloatHandleEmpty
from jdaviz.core.registries import tray_registry
from jdaviz.core.template_mixin import PluginTemplateMixin, DatasetSelectMixin
from traitlets import Bool, List, Unicode, observe
import sounddevice as sd


__all__ = ['SonifyData']


@tray_registry('cubeviz-sonify-data', label="Sonify Data",
               viewer_requirements=['spectrum', 'image'])
class SonifyData(PluginTemplateMixin, DatasetSelectMixin):
    template_file = __file__, "sonify_data.vue"

    sample_rate = IntHandleEmpty(44100).tag(sync=True)
    buffer_size = IntHandleEmpty(2048).tag(sync=True)
    assidx = FloatHandleEmpty(2.5).tag(sync=True)
    ssvidx = FloatHandleEmpty(0.65).tag(sync=True)
    eln    = Bool(False).tag(sync=True)
    wavemin = FloatHandleEmpty(15800).tag(sync=True)
    wavemax = FloatHandleEmpty(16000).tag(sync=True) 
    audfrqmin = FloatHandleEmpty(50).tag(sync=True)
    audfrqmax = FloatHandleEmpty(1500).tag(sync=True)
    pccut = IntHandleEmpty(20).tag(sync=True)

    sound_devices_items = List().tag(sync=True)
    sound_devices_selected = Unicode('').tag(sync=True)
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.sound_devices_items = [device['name'] for device in sd.query_devices()]
        self.sound_devices_selected = self.sound_devices_items[sd.default.device[1]]

    def vue_sonify_cube(self, *args):
        viewer = self.app.get_viewer('flux-viewer')
        # Get index of selected device since name may not be unique
        selected_device_index = self.sound_devices_items.index(self.sound_devices_selected)
        viewer.get_sonified_cube(self.sample_rate, self.buffer_size, selected_device_index,
                                 self.assidx, self.ssvidx, self.pccut, self.audfrqmin,
                                 self.audfrqmax, self.eln)
