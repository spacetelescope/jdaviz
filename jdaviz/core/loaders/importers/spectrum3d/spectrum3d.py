import numpy as np
from traitlets import Any, Bool, List, Unicode, observe
from astropy import units as u
from astropy.nddata import StdDevUncertainty
from specutils import Spectrum

from jdaviz.core.custom_units_and_equivs import PIX2
from jdaviz.core.events import SnackbarMessage
from jdaviz.core.registries import loader_importer_registry, viewer_registry
from jdaviz.core.loaders.importers import (BaseImporterToDataCollection,
                                           SpectrumInputExtensionsMixin)
from jdaviz.core.loaders.importers.spectrum_common import _spectrum_assign_component_type
from jdaviz.core.loaders.importers.image.image import _spatial_assign_component_type
from jdaviz.core.template_mixin import (AutoTextField,
                                        SelectPluginComponent,
                                        ViewerSelectCreateNew)
from jdaviz.core.unit_conversion_utils import (check_if_unit_is_per_solid_angle,
                                               _eqv_flux_to_sb_pixel)
from jdaviz.core.user_api import ImporterUserApi


__all__ = ['Spectrum3DImporter']


@loader_importer_registry('3D Spectrum')
class Spectrum3DImporter(BaseImporterToDataCollection, SpectrumInputExtensionsMixin):
    template_file = __file__, "./spectrum3d.vue"
    parser_preference = ['fits', 'asdf', 'specutils.Spectrum']

    # Uncertainty Cube
    unc_data_label_value = Unicode().tag(sync=True)
    unc_data_label_default = Unicode().tag(sync=True)
    unc_data_label_auto = Bool(True).tag(sync=True)
    unc_data_label_invalid_msg = Unicode().tag(sync=True)

    # Uncertainty Viewer
    has_unc = Bool(False).tag(sync=True)
    unc_viewer_create_new_items = List([]).tag(sync=True)
    unc_viewer_create_new_selected = Unicode().tag(sync=True)

    unc_viewer_items = List([]).tag(sync=True)
    unc_viewer_selected = Any([]).tag(sync=True)
    unc_viewer_multiselect = Bool(True).tag(sync=True)

    unc_viewer_label_value = Unicode().tag(sync=True)
    unc_viewer_label_default = Unicode().tag(sync=True)
    unc_viewer_label_auto = Bool(True).tag(sync=True)
    unc_viewer_label_invalid_msg = Unicode().tag(sync=True)

    # Mask Cube
    mask_data_label_value = Unicode().tag(sync=True)
    mask_data_label_default = Unicode().tag(sync=True)
    mask_data_label_auto = Bool(True).tag(sync=True)
    mask_data_label_invalid_msg = Unicode().tag(sync=True)

    # Mask Viewer
    has_mask = Bool(False).tag(sync=True)
    mask_viewer_create_new_items = List([]).tag(sync=True)
    mask_viewer_create_new_selected = Unicode().tag(sync=True)

    mask_viewer_items = List([]).tag(sync=True)
    mask_viewer_selected = Any([]).tag(sync=True)
    mask_viewer_multiselect = Bool(True).tag(sync=True)

    mask_viewer_label_value = Unicode().tag(sync=True)
    mask_viewer_label_default = Unicode().tag(sync=True)
    mask_viewer_label_auto = Bool(True).tag(sync=True)
    mask_viewer_label_invalid_msg = Unicode().tag(sync=True)

    # Extraction Options
    auto_extract = Bool(True).tag(sync=True)
    function_items = List().tag(sync=True)
    function_selected = Unicode('Sum').tag(sync=True)
    # Don't load uncertainty and mask as separate cubes, e.g. for plugin results
    flux_only = Bool(False).tag(sync=True)

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

        # FLUX CUBE
        if self.default_data_label_from_resolver:
            self.data_label_default = self.default_data_label_from_resolver
        elif self.config == 'cubeviz':
            self.data_label_default = '3D Spectrum [FLUX]'
        else:
            self.data_label_default = '3D Spectrum'

        if self.config == 'cubeviz':
            self.viewer.selected = ['flux-viewer']

        # UNCERTAINTY CUBE
        self.has_unc = self.spectrum.uncertainty is not None
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

        # MASK CUBE
        self.has_mask = self.spectrum.mask is not None
        self.mask_data_label = AutoTextField(self,
                                             'mask_data_label_value',
                                             'mask_data_label_default',
                                             'mask_data_label_auto',
                                             'mask_data_label_invalid_msg')

        self.mask_viewer = ViewerSelectCreateNew(self,
                                                 'mask_viewer_items',
                                                 'mask_viewer_selected',
                                                 'mask_viewer_create_new_items',
                                                 'mask_viewer_create_new_selected',
                                                 'mask_viewer_label_value',
                                                 'mask_viewer_label_default',
                                                 'mask_viewer_label_auto',
                                                 'mask_viewer_label_invalid_msg',
                                                 multiselect='mask_viewer_multiselect',
                                                 default_mode='empty')
        # TODO: default label separate from viewer label (so we can call it mask-viewer, etc)
        supported_viewers = [{'label': '3D Spectrum',
                              'reference': 'cubeviz-image-viewer'}]
        if self.app.config == 'deconfigged':
            self.mask_viewer_create_new_items = supported_viewers

        self.mask_viewer.add_filter(viewer_in_registry_names(supported_viewers))
        if self.config == 'cubeviz':
            self.mask_viewer.selected = []
        else:
            self.mask_viewer.selected = []

        # AUTO-EXTRACTION
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
        expose = ['auto_extract', 'ext_data_label', 'ext_viewer', 'flux_only']
        if self.has_unc:
            expose += ['unc_data_label', 'unc_viewer']
        if self.has_mask:
            expose += ['mask_data_label', 'mask_viewer']
        expose += ['extension']
        if self.has_unc:
            expose += ['unc_extension']
        if self.has_mask:
            expose += ['mask_extension']
        return ImporterUserApi(self, expose)

    @property
    def is_valid(self):
        if self.app.config not in ('deconfigged', 'cubeviz'):
            # NOTE: temporary during deconfig process
            return False
        try:
            if self.spectrum.flux.ndim != 3:
                return False
        except Exception:
            return False

        try:
            self.output
        except Exception:
            return False
        return True

    @observe('data_label_value', 'function_selected')
    def _data_label_changed(self, msg={}):
        base = self.data_label_value.strip('[FLUX]').strip()
        self.ext_data_label_default = f"{base} ({self.function_selected.lower()})"
        self.unc_data_label_default = f"{base} [UNC]"
        self.mask_data_label_default = f"{base} [MASK]"

    @property
    def supported_flux_ndim(self):
        return 3

    @property
    def default_spectral_axis_index(self):
        return 0

    @property
    def output(self):
        sp = self.spectrum

        # convert flux and uncertainty to per-pix2 if input is not a surface brightness
        if not check_if_unit_is_per_solid_angle(sp.flux.unit):
            target_flux_unit = sp.flux.unit / PIX2
        elif check_if_unit_is_per_solid_angle(sp.flux.unit, return_unit=True) == "spaxel":
            # We need to convert spaxel to pix2, since spaxel isn't fully supported by astropy
            # This is horribly ugly but just multiplying by u.Unit("spaxel") doesn't work
            target_flux_unit = sp.flux.unit * u.Unit('spaxel') / PIX2
        else:
            target_flux_unit = sp.flux.unit

        # handle scale factors when they are included in the unit
        if not np.isclose(target_flux_unit.scale, 1, rtol=1e-5):
            target_flux_unit = target_flux_unit / target_flux_unit.scale

        if target_flux_unit == sp.flux.unit:
            return sp

        # In the case of a np.array, it is loaded into a Spectrum without WCS,
        # so specutils creates a SpectralGWCS by default. We need this WCS later on
        # for spatial region handling, so we store a copy of that WCS here.
        if '_orig_spatial_wcs' not in sp.meta:
            sp.meta['_orig_spatial_wcs'] = sp.wcs

        return sp.with_flux_unit(target_flux_unit, equivalencies=_eqv_flux_to_sb_pixel())

    def __call__(self):
        # get a copy of all requested data-labels before additional data entries changes defaults
        data_label = self.data_label_value
        unc_data_label = self.unc_data_label_value
        mask_data_label = self.mask_data_label_value
        ext_data_label = self.ext_data_label_value

        super().__call__()
        # TODO: this will need to be removed when removing restriction of a single flux cube
        if not getattr(self.app._jdaviz_helper, '_loaded_flux_cube', None):
            self.app._jdaviz_helper._loaded_flux_cube = self.app.data_collection[data_label]

        if self.has_unc and not self.flux_only:
            # TODO: detect if uncertainty exists and hide section from UI
            uncert = Spectrum(spectral_axis=self.output.spectral_axis,
                              flux=self.output.uncertainty.represent_as(StdDevUncertainty).quantity,
                              wcs=self.output.wcs,
                              meta=self.output.meta,
                              spectral_axis_index=self.output.spectral_axis_index)
            self.add_to_data_collection(uncert,
                                        unc_data_label,
                                        viewer_select=self.unc_viewer)
            # TODO: this will need to be removed when removing restriction of a single flux cube
            self.app._jdaviz_helper._loaded_uncert_cube = self.app.data_collection[unc_data_label]

        if self.has_mask and not self.flux_only:
            mask = Spectrum(spectral_axis=self.output.spectral_axis,
                            flux=self.output.mask * u.dimensionless_unscaled,
                            wcs=self.output.wcs,
                            meta=self.output.meta,
                            spectral_axis_index=self.output.spectral_axis_index)
            self.add_to_data_collection(mask,
                                        mask_data_label,
                                        viewer_select=self.mask_viewer)
            # TODO: this will need to be removed when removing restriction of a single flux cube
            self.app._jdaviz_helper._loaded_mask_cube = self.app.data_collection[mask_data_label]

        if not self.auto_extract:
            return

        try:
            spext = self.app.get_tray_item_from_name('spectral-extraction-3d')
            ext = spext._extract_in_new_instance(dataset=data_label,
                                                 function=self.function.selected,
                                                 auto_update=False,
                                                 add_data=False)
            # we'll add the data manually instead of through add_results_from_plugin
            # but still want to preserve the plugin metadata
            ext.meta['plugin'] = spext._plugin_name
        except Exception as e:
            ext = None
            msg = SnackbarMessage(
                "Automatic spectrum extraction failed. See the 3D spectral extraction"
                " plugin to perform a custom extraction",
                color='error', sender=self, timeout=10000, traceback=e)
        else:
            msg = SnackbarMessage(
                "The extracted 1D spectrum was generated automatically."
                " See the 3D spectral extraction plugin for details or to"
                " perform a custom extraction.",
                color='warning', sender=self, timeout=10000)
        self.app.hub.broadcast(msg)

        if ext is not None:
            self.add_to_data_collection(ext, ext_data_label, viewer_select=self.ext_viewer)

    def assign_component_type(self, comp_id, comp, units, physical_type):
        comp_type = _spatial_assign_component_type(comp_id, comp, units, physical_type)
        return _spectrum_assign_component_type(comp_id, comp, units, comp_type)
