from specutils import Spectrum1D

from jdaviz.core.registries import loader_importer_registry
from jdaviz.core.loaders.importers import BaseImporterToDataCollection


__all__ = ['Spectrum1DImporter']


@loader_importer_registry('1D Spectrum')
class Spectrum1DImporter(BaseImporterToDataCollection):
    template_file = __file__, "../to_dc_with_label.vue"

    @property
    def is_valid(self):
        if self.app.config not in ('specviz', 'specviz2d'):
            # NOTE: temporary during deconfig process
            return False
        return isinstance(self.input, Spectrum1D) and self.input.flux.ndim == 1

    @property
    def default_viewer(self):
        # returns the registry name of the default viewer
        # only used if `show_in_viewer=True` and no existing viewers can accept the data
        return 'specviz-profile-viewer'
