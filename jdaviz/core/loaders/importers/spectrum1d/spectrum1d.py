import numpy as np
from specutils import Spectrum

from jdaviz.core.events import SnackbarMessage
from jdaviz.core.registries import loader_importer_registry
from jdaviz.core.loaders.importers import BaseImporterToDataCollection


__all__ = ['SpectrumImporter']


@loader_importer_registry('1D Spectrum')
class SpectrumImporter(BaseImporterToDataCollection):
    template_file = __file__, "../to_dc_with_label.vue"

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

    @property
    def is_valid(self):
        if self.app.config not in ('deconfigged', 'specviz', 'specviz2d', 'cubeviz'):
            # cubeviz allowed for cubeviz.specviz.load_data support
            # NOTE: temporary during deconfig process
            return False
        return isinstance(self.input, Spectrum) and self.input.flux.ndim == 1

    @property
    def default_viewer_reference(self):
        # returns the registry name of the default viewer
        # only used if `show_in_viewer=True` and no existing viewers can accept the data
        return 'spectrum-1d-viewer'

    @property
    def output(self):
        # if the entire uncert. array is Nan and the data is not, model fitting won't
        # work (more generally, if uncert[i] is nan/inf and flux[i] is not, fitting will
        # fail, but just deal with the all nan case here since it is straightforward).
        # set uncerts. to None if they are all nan/inf, and display a warning message.
        data = self.input
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
