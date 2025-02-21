from specutils import Spectrum1D, SpectrumList

from jdaviz.core.registries import loader_importer_registry
from jdaviz.core.loaders.importers import BaseImporterToDataCollection


@loader_importer_registry('1D Spectrum List')
class Spectrum2DAsListImporter(BaseImporterToDataCollection):
    template_file = __file__, "spectrum2d_as_list.vue"

    @property
    def is_valid(self):
        if self.app.config != 'specviz':
            # NOTE: temporary during deconfig process
            return False
        # TODO: should this be split into two loaders?
        # should a loader take a single input type, output a single output type,
        # or just have a consistent data_label and viewer?
        return (isinstance(self.input, SpectrumList) or (isinstance(self.input, Spectrum1D)
                and self.input.flux.ndim == 2))

    @property
    def output(self):
        if not self.is_valid:  # pragma: nocover
            return None
        if isinstance(self.input, SpectrumList):
            return self.input
        elif isinstance(self.input, Spectrum1D):
            def this_row(field, i):
                if field is None:
                    return None
                return field[i, :]

            return SpectrumList([Spectrum1D(spectral_axis=self.input.spectral_axis,
                                            flux=this_row(self.input.flux, i),
                                            uncertainty=this_row(self.input.uncertainty, i),
                                            mask=this_row(self.input.mask, i),
                                            meta=self.input.meta)
                                 for i in range(self.input.flux.shape[0])])
        else:
            raise NotImplementedError()  # pragma: nocover

    @property
    def default_data_label(self):
        return '1D Spectrum'

    @property
    def default_viewer(self):
        # returns the registry name of the default viewer
        # only used if `show_in_viewer=True` and no existing viewers can accept the data
        return 'specviz-profile-viewer'
