from traitlets import Any, Bool, List, Unicode, observe
from astropy.nddata import StdDevUncertainty
from specutils import Spectrum

from jdaviz.core.events import SnackbarMessage
from jdaviz.core.registries import loader_importer_registry, viewer_registry
from jdaviz.core.loaders.importers import BaseImporterToDataCollection
from jdaviz.core.template_mixin import (AutoTextField,
                                        SelectPluginComponent,
                                        ViewerSelectCreateNew)
from jdaviz.core.user_api import ImporterUserApi


__all__ = ['Spectrum3DImporter']


@loader_importer_registry('3D Spectrum')
class Spectrum3DImporter(BaseImporterToDataCollection):
    template_file = __file__, "./spectrum3d.vue"
    # TODO: add fits support with unc extension selection
    parser_preference = ['specutils.Spectrum']

    # Uncertainty Cube
    unc_data_label_value = Unicode().tag(sync=True)
    unc_data_label_default = Unicode().tag(sync=True)
    unc_data_label_auto = Bool(True).tag(sync=True)
    unc_data_label_invalid_msg = Unicode().tag(sync=True)

    # Uncertainty Viewer
    unc_viewer_create_new_items = List([]).tag(sync=True)
    unc_viewer_create_new_selected = Unicode().tag(sync=True)

    unc_viewer_items = List([]).tag(sync=True)
    unc_viewer_selected = Any([]).tag(sync=True)
    unc_viewer_multiselect = Bool(True).tag(sync=True)

    unc_viewer_label_value = Unicode().tag(sync=True)
    unc_viewer_label_default = Unicode().tag(sync=True)
    unc_viewer_label_auto = Bool(True).tag(sync=True)
    unc_viewer_label_invalid_msg = Unicode().tag(sync=True)

    # Extraction Options
    auto_extract = Bool(True).tag(sync=True)
    function_items = List().tag(sync=True)
    function_selected = Unicode('Sum').tag(sync=True)

    # Extracted Data
    ext_data_label_value = Unicode().tag(sync=True)
    ext_data_label_default = Unicode().tag(sync=True)
    ext_data_label_auto = Bool(True).tag(sync=True)
    ext_data_label_invalid_msg = Unicode().tag(sync=True)

    # Extracted Viewer
    ext_viewer_create_new_items = List([]).tag(sync=True)
    ext_viewer_create_new_selected = Unicode().tag(sync=True)

    ext_viewer_items = List([]).tag(sync=True)
    ext_viewer_selected = Any([]).tag(sync=True)
    ext_viewer_multiselect = Bool(True).tag(sync=True)

    ext_viewer_label_value = Unicode().tag(sync=True)
    ext_viewer_label_default = Unicode().tag(sync=True)
    ext_viewer_label_auto = Bool(True).tag(sync=True)
    ext_viewer_label_invalid_msg = Unicode().tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        def viewer_in_registry_names(supported_viewers):
            def viewer_filter(viewer):
                classes = [viewer_registry.members.get(item.get('reference')).get('cls')
                           for item in supported_viewers]
                return isinstance(viewer, tuple(classes))
            return viewer_filter

        if self.default_data_label_from_resolver:
            self.data_label_default = self.default_data_label_from_resolver
        else:
            self.data_label_default = '3D Spectrum'

        if self.config == 'cubeviz':
            self.viewer.selected = ['flux-viewer']

        self.unc_data_label = AutoTextField(self,
                                            'unc_data_label_value',
                                            'unc_data_label_default',
                                            'unc_data_label_auto',
                                            'unc_data_label_invalid_msg')

        self.unc_viewer = ViewerSelectCreateNew(self,
                                                'unc_viewer_items',
                                                'unc_viewer_selected',
                                                'unc_viewer_create_new_items',
                                                'unc_viewer_create_new_selected',
                                                'unc_viewer_label_value',
                                                'unc_viewer_label_default',
                                                'unc_viewer_label_auto',
                                                'unc_viewer_label_invalid_msg',
                                                multiselect='unc_viewer_multiselect',
                                                default_mode='empty')
        # TODO: default label separate from viewer label (so we can call it unc-viewer, etc)
        supported_viewers = [{'label': '3D Spectrum',
                              'reference': 'cubeviz-image-viewer'}]
        if self.app.config == 'deconfigged':
            self.unc_viewer_create_new_items = supported_viewers

        self.unc_viewer.add_filter(viewer_in_registry_names(supported_viewers))
        if self.config == 'cubeviz':
            self.unc_viewer.selected = ['uncert-viewer']
        else:
            self.unc_viewer.select_default()

        self.function = SelectPluginComponent(
            self,
            items='function_items',
            selected='function_selected',
            manual_options=['Mean', 'Min', 'Max', 'Sum']
        )

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

        self.ext_viewer.add_filter(viewer_in_registry_names(supported_viewers))
        self.ext_viewer.select_default()

    @staticmethod
    def _get_supported_viewers():
        return [{'label': '3D Spectrum', 'reference': 'cubeviz-image-viewer'}]

    @property
    def user_api(self):
        expose = ['unc_data_label', 'unc_viewer',
                  'auto_extract', 'ext_data_label', 'ext_viewer']
        if self.input_hdulist:
            expose += ['extension']
        return ImporterUserApi(self, expose)

    @property
    def is_valid(self):
        if self.app.config not in ('deconfigged', 'cubeviz'):
            # NOTE: temporary during deconfig process
            return False
        if not isinstance(self.input, Spectrum):
            return False
        if not self.input.flux.ndim == 3:
            return False
        try:
            self.output
        except Exception:
            return False
        return True

    @observe('data_label_value', 'function_selected')
    def _data_label_changed(self, msg={}):
        self.ext_data_label_default = f"{self.data_label_value} ({self.function_selected})"
        self.unc_data_label_default = f"{self.data_label_value} [UNC]"

    @property
    def output(self):
        return self.input

    def __call__(self):
        # get a copy of both of these before additional data entries changes defaults
        data_label = self.data_label_value
        unc_data_label = self.unc_data_label_value
        ext_data_label = self.ext_data_label_value

        super().__call__()
        # TODO: this will need to be removed when removing restriction of a single flux cube
        self.app._jdaviz_helper._loaded_flux_cube = self.app.data_collection[data_label]

        if self.output.uncertainty is not None:
            # TODO: detect if uncertainty exists and hide section from UI
            uncert = Spectrum(spectral_axis=self.output.spectral_axis,
                              flux=self.output.uncertainty.represent_as(StdDevUncertainty).quantity,
                              wcs=self.output.wcs,
                              meta=self.output.meta)
            self.add_to_data_collection(uncert,
                                        unc_data_label,
                                        viewer_select=self.unc_viewer)
            # TODO: this will need to be removed when removing restriction of a single flux cube
            self.app._jdaviz_helper._loaded_uncert_cube = self.app.data_collection[unc_data_label]

        if not self.auto_extract:
            return

        try:
            spext = self.app.get_tray_item_from_name('spectral-extraction-3d')
            ext = spext._extract_in_new_instance(dataset=data_label,
                                                 function=self.function.selected,
                                                 auto_update=False,
                                                 add_data=False)
        except Exception:
            ext = None
            msg = SnackbarMessage(
                "Automatic spectrum extraction failed. See the 3D spectral extraction"
                " plugin to perform a custom extraction",
                color='error', sender=self, timeout=10000)
        else:
            msg = SnackbarMessage(
                "The extracted 1D spectrum was generated automatically."
                " See the 3D spectral extraction plugin for details or to"
                " perform a custom extraction.",
                color='warning', sender=self, timeout=10000)
        self.app.hub.broadcast(msg)

        if ext is not None:
            self.add_to_data_collection(ext, ext_data_label, viewer_select=self.ext_viewer)
