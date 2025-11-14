from traitlets import Any, Bool, List, Unicode, observe

from jdaviz.core.events import SnackbarMessage
from jdaviz.core.registries import loader_importer_registry, viewer_registry
from jdaviz.core.loaders.importers import (BaseImporterToDataCollection,
                                           SpectrumInputExtensionsMixin,
                                           _spectrum_assign_component_type)
from jdaviz.core.template_mixin import (AutoTextField,
                                        ViewerSelectCreateNew)
from jdaviz.core.user_api import ImporterUserApi


__all__ = ['Spectrum2DImporter']


@loader_importer_registry('2D Spectrum')
class Spectrum2DImporter(BaseImporterToDataCollection, SpectrumInputExtensionsMixin):
    template_file = __file__, "./spectrum2d.vue"
    parser_preference = ['fits', 'asdf', 'specutils.Spectrum']

    auto_extract = Bool(True).tag(sync=True)

    ext_data_label_value = Unicode().tag(sync=True)
    ext_data_label_default = Unicode().tag(sync=True)
    ext_data_label_auto = Bool(True).tag(sync=True)
    ext_data_label_invalid_msg = Unicode().tag(sync=True)

    ext_viewer_create_new_items = List([]).tag(sync=True)
    ext_viewer_create_new_selected = Unicode().tag(sync=True)
    # No uncertainty viewer for 2D
    has_unc = Bool(False).tag(sync=True)

    ext_viewer_items = List([]).tag(sync=True)
    ext_viewer_selected = Any([]).tag(sync=True)
    ext_viewer_multiselect = Bool(True).tag(sync=True)

    ext_viewer_label_value = Unicode().tag(sync=True)
    ext_viewer_label_default = Unicode().tag(sync=True)
    ext_viewer_label_auto = Bool(True).tag(sync=True)
    ext_viewer_label_invalid_msg = Unicode().tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.default_data_label_from_resolver:
            self.data_label_default = self.default_data_label_from_resolver
        elif self.app.config == 'specviz2d':
            self.data_label_default = '2D Spectrum'

        self.ext_data_label = AutoTextField(self,
                                            'ext_data_label_value',
                                            'ext_data_label_default',
                                            'ext_data_label_auto',
                                            'ext_data_label_invalid_msg')

        self.ext_viewer = ViewerSelectCreateNew(self,
                                                'ext_viewer_items',
                                                'ext_viewer_selected',
                                                'ext_viewer_create_new_items',
                                                'ext_viewer_create_new_selected',
                                                'ext_viewer_label_value',
                                                'ext_viewer_label_default',
                                                'ext_viewer_label_auto',
                                                'ext_viewer_label_invalid_msg',
                                                multiselect='ext_viewer_multiselect',
                                                default_mode='empty')
        supported_viewers = [{'label': '1D Spectrum',
                              'reference': 'spectrum-1d-viewer'}]
        if self.app.config == 'deconfigged':
            self.ext_viewer_create_new_items = supported_viewers

        def viewer_in_registry_names(viewer):
            classes = [viewer_registry.members.get(item.get('reference')).get('cls')
                       for item in supported_viewers]
            return isinstance(viewer, tuple(classes))
        self.ext_viewer.add_filter(viewer_in_registry_names)
        self.ext_viewer.select_default()

    @staticmethod
    def _get_supported_viewers():
        return [{'label': '2D Spectrum', 'reference': 'spectrum-2d-viewer'}]

    @property
    def user_api(self):
        expose = ['auto_extract', 'ext_data_label', 'ext_viewer',
                  'extension', 'unc_extension', 'mask_extension']
        return ImporterUserApi(self, expose)

    @property
    def is_valid(self):
        if self.app.config not in ('deconfigged', 'specviz2d'):
            # NOTE: temporary during deconfig process
            return False
        try:
            if self.spectrum.flux.ndim != 2:
                return False
        except Exception:
            return False
        try:
            self.output
        except Exception:
            return False
        return True

    @observe('data_label_value')
    def _data_label_changed(self, msg={}):
        self.ext_data_label_default = f"{self.data_label_value} (auto-ext)"

    @property
    def output(self):
        return self.spectrum

    def assign_component_type(self, comp_id, comp, units, physical_type):
        return _spectrum_assign_component_type(comp_id, comp, units, physical_type)

    def __call__(self):
        # get a copy of both of these before additional data entries changes defaults
        data_label = self.data_label_value
        ext_data_label = self.ext_data_label_value

        super().__call__()

        if not self.auto_extract:
            return

        try:
            spext = self.app.get_tray_item_from_name('spectral-extraction-2d')
            ext = spext._extract_in_new_instance(dataset=data_label,
                                                 add_data=False)
        except Exception as e:
            ext = None
            msg = SnackbarMessage(
                "Automatic spectrum extraction failed. See the 2D spectral extraction"
                " plugin to perform a custom extraction",
                color='error', sender=self, timeout=10000, traceback=e)
        else:
            msg = SnackbarMessage(
                "The extracted 1D spectrum was generated automatically."
                " See the 2D spectral extraction plugin for details or to"
                " perform a custom extraction.",
                color='warning', sender=self, timeout=10000)
        self.app.hub.broadcast(msg)

        if ext is not None:
            self.add_to_data_collection(ext, ext_data_label, viewer_select=self.ext_viewer)
