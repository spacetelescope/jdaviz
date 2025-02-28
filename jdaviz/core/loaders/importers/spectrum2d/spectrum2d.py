from traitlets import Bool, Unicode, observe
from specutils import Spectrum1D

from jdaviz.core.events import SnackbarMessage
from jdaviz.core.registries import loader_importer_registry
from jdaviz.core.loaders.importers import BaseImporterToDataCollection
from jdaviz.core.template_mixin import AutoTextField
from jdaviz.core.user_api import ImporterUserApi


__all__ = ['Spectrum2DImporter']


@loader_importer_registry('2D Spectrum')
class Spectrum2DImporter(BaseImporterToDataCollection):
    template_file = __file__, "./spectrum2d.vue"

    auto_extract = Bool(True).tag(sync=True)

    ext_data_label_value = Unicode().tag(sync=True)
    ext_data_label_default = Unicode().tag(sync=True)
    ext_data_label_auto = Bool(True).tag(sync=True)
    ext_data_label_invalid_msg = Unicode().tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.ext_data_label = AutoTextField(self,
                                            'ext_data_label_value',
                                            'ext_data_label_default',
                                            'ext_data_label_auto',
                                            'ext_data_label_invalid_msg')

    @property
    def user_api(self):
        return ImporterUserApi(self, ['auto_extract', 'ext_data_label'])

    @property
    def is_valid(self):
        if self.app.config not in ('specviz', 'specviz2d'):
            # NOTE: temporary during deconfig process
            return False
        return isinstance(self.input, Spectrum1D) and self.input.flux.ndim == 2

    @property
    def default_viewer_reference(self):
        # returns the registry name of the default viewer
        # only used if `show_in_viewer=True` and no existing viewers can accept the data
        return 'mosviz-profile-2d-viewer'

    @observe('data_label_value')
    def _data_label_changed(self, msg={}):
        self.ext_data_label_default = f"{self.data_label_value} (auto-ext)"

    def __call__(self):
        # get a copy of both of these before additional data entries changes defaults
        data_label = self.data_label_value
        ext_data_label = self.ext_data_label_value

        super().__call__()

        if not self.auto_extract:
            return

        try:
            ext = self.app.get_tray_item_from_name('spectral-extraction')._extract_in_new_instance(dataset=data_label, add_data=False)
        except Exception:
            raise
            ext = None
            msg = SnackbarMessage(
                "Automatic spectrum extraction failed. See the spectral extraction"
                " plugin to perform a custom extraction",
                color='error', sender=self, timeout=10000)
        else:
            msg = SnackbarMessage(
                "The extracted 1D spectrum was generated automatically."
                " See the spectral extraction plugin for details or to"
                " perform a custom extraction.",
                color='warning', sender=self, timeout=10000)
        self.app.hub.broadcast(msg)

        if ext is not None:
            self.add_to_data_collection(ext, ext_data_label, show_in_viewer=False)
            self.load_into_viewer(ext_data_label, "specviz-profile-viewer")
