import numpy as np

from jdaviz.core.events import SnackbarMessage
from jdaviz.core.registries import loader_importer_registry
from jdaviz.core.loaders.importers import (BaseImporterToDataCollection,
                                           SpectrumInputExtensionsMixin,
                                           _spectrum_assign_component_type)
from jdaviz.core.user_api import ImporterUserApi


__all__ = ['SpectrumImporter']


@loader_importer_registry('1D Spectrum')
class SpectrumImporter(BaseImporterToDataCollection, SpectrumInputExtensionsMixin):
    template_file = __file__, "./spectrum1d.vue"
    parser_preference = ['fits', 'asdf', 'specutils.Spectrum']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.default_data_label_from_resolver:
            self.data_label_default = self.default_data_label_from_resolver
        elif self.app.config == 'specviz':
            self.data_label_default = '1D Spectrum'
        elif self.app.config == 'specviz2d':
            self.data_label_default = '1D Spectrum'
        else:
            self.data_label_default = '1D Spectrum'

    @staticmethod
    def _get_supported_viewers():
        return [{'label': '1D Spectrum', 'reference': 'spectrum-1d-viewer'}]

    @property
    def is_valid(self):
        if self.app.config not in ('deconfigged', 'specviz', 'specviz2d', 'cubeviz'):
            # NOTE: temporary during deconfig process
            return False
        try:
            if self.spectrum.flux.ndim != 1:
                return False
        except Exception:
            return False
        try:
            self.output
        except Exception:
            return False
        return True

    @property
    def user_api(self):
        expose = ['extension', 'unc_extension', 'mask_extension']
        return ImporterUserApi(self, expose)

    @property
    def supported_flux_ndim(self):
        return 1

    @property
    def output(self):
        # if the entire uncert. array is Nan and the data is not, model fitting won't
        # work (more generally, if uncert[i] is nan/inf and flux[i] is not, fitting will
        # fail, but just deal with the all nan case here since it is straightforward).
        # set uncerts. to None if they are all nan/inf, and display a warning message.
        data = self.spectrum
        if data.uncertainty is not None:
            uncerts_finite = np.isfinite(data.uncertainty.array)
            if not np.any(uncerts_finite):
                data.uncertainty = None
                set_nans_to_none = True

                if set_nans_to_none:
                    # alert user that we have changed their all-nan uncertainty array to None
                    msg = 'All uncertainties are nonfinite, replacing with uncertainty=None.'
                    self.app.hub.broadcast(SnackbarMessage(msg, color="warning", sender=self.app))
        return data

    def assign_component_type(self, comp_id, comp, units, physical_type):
        return _spectrum_assign_component_type(comp_id, comp, units, physical_type)
