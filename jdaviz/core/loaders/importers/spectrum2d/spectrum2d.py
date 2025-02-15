from specutils import Spectrum1D

from jdaviz.core.registries import loader_importer_registry
from jdaviz.core.loaders.importers import BaseImporterToDataCollection


@loader_importer_registry('2D Spectrum')
class Spectrum2DImporter(BaseImporterToDataCollection):
    template_file = __file__, "spectrum2d.vue"

    @property
    def is_valid(self):
        return isinstance(self.input, Spectrum1D) and self.input.flux.ndim == 2

    @property
    def default_viewer(self):
        # returns the registry name of the default viewer
        # only used if `show_in_viewer=True` and no existing viewers can accept the data
        return 'mosviz-profile-2d-viewer'

