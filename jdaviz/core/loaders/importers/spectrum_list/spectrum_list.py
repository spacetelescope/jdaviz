import itertools
from specutils import Spectrum1D, SpectrumList, SpectrumCollection

from jdaviz.core.registries import loader_importer_registry
from jdaviz.core.loaders.importers import BaseImporterToDataCollection


__all__ = ['SpectrumListImporter']


@loader_importer_registry('1D Spectrum List')
class SpectrumListImporter(BaseImporterToDataCollection):
    template_file = __file__, "spectrum_list.vue"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.data_label_default = '1D Spectrum'

    @property
    def is_valid(self):
        if self.app.config not in ('deconfigged', 'specviz'):
            # NOTE: temporary during deconfig process
            return False
        # TODO: should this be split into two loaders?
        # should a loader take a single input type, output a single output type,
        # or just have a consistent data_label and viewer?
        return (isinstance(self.input, (SpectrumList, SpectrumCollection))
                or (isinstance(self.input, Spectrum1D) and self.input.flux.ndim == 2))

    @property
    def output(self):
        if not self.is_valid:  # pragma: nocover
            return None

        def this_row(field, i):
            if field is None:
                return None
            return field[i, :]

        def input_to_list_of_spec(inp):
            if isinstance(inp, Spectrum1D):
                if inp.flux.ndim == 1:
                    return [inp]
                return [Spectrum1D(spectral_axis=inp.spectral_axis,
                                   flux=this_row(inp.flux, i),
                                   uncertainty=this_row(inp.uncertainty, i),
                                   mask=this_row(inp.mask, i),
                                   meta=inp.meta)
                        for i in range(inp.flux.shape[0])]
            elif isinstance(inp, (SpectrumList, SpectrumCollection)):
                return itertools.chain(*[input_to_list_of_spec(spec) for spec in inp])
            else:
                raise NotImplementedError(f"{inp} is not supported")

        return SpectrumList(input_to_list_of_spec(self.input))

    @property
    def default_viewer_reference(self):
        # returns the registry name of the default viewer
        # only used if `show_in_viewer=True` and no existing viewers can accept the data
        return 'spectrum-1d-viewer'

    def __call__(self):
        data_label = self.data_label_value
        with self.app._jdaviz_helper.batch_load():
            for i, spec in enumerate(self.output):
                self.add_to_data_collection(spec, f"{data_label}_{i}", show_in_viewer=True)
