from specutils import Spectrum1D

from jdaviz.core.registries import loader_importer_registry
from jdaviz.core.loaders.importers import BaseImporter


@loader_importer_registry('1D Spectrum')
class Spectrum1DImporter(BaseImporter):
    template_file = __file__, "spectrum1d.vue"

    @property
    def is_valid(self):
        return isinstance(self.input, Spectrum1D) and self.input.flux.ndim == 1

    @property
    def default_viewer(self):
        # returns the registry name of the default viewer
        # only used if `show_in_viewer=True` and no existing viewers can accept the data
        return 'specviz-profile-viewer'