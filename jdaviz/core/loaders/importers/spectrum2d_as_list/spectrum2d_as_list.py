from specutils import Spectrum1D, SpectrumList

from jdaviz.core.registries import loader_importer_registry
from jdaviz.core.loaders.importers import BaseImporterToDataCollection


__all__ = ['Spectrum2DAsListImporter']


@loader_importer_registry('1D Spectrum List')
class Spectrum2DAsListImporter(BaseImporterToDataCollection):
    template_file = __file__, "spectrum2d_as_list.vue"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.data_label_default = '1D Spectrum'

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
            raise NotImplementedError(f"{self.input} is not supported")  # pragma: nocover

    @property
    def default_viewer(self):
        # returns the registry name of the default viewer
        # only used if `show_in_viewer=True` and no existing viewers can accept the data
        return 'specviz-profile-viewer'

    def __call__(self, data_label=None):
        if data_label is None:
            data_label = self.data_label_value
        with self.app._jdaviz_helper.batch_load():
            for i, spec in enumerate(self.output):
                self.add_to_data_collection(spec, f"{data_label}_{i}", show_in_viewer=True)
