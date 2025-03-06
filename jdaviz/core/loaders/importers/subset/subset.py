from regions import Regions
from specutils import SpectralRegion


from jdaviz.core.registries import loader_importer_registry
from jdaviz.core.loaders.importers import BaseImporterToPlugin


__all__ = ['SubsetImporter']


@loader_importer_registry('Subset')
class SubsetImporter(BaseImporterToPlugin):
    template_file = __file__, "subset.vue"

    @property
    def is_valid(self):
        return (isinstance(self.input, (Regions, SpectralRegion))
                and self.has_default_plugin)

    @property
    def default_plugin(self):
        return 'Subset Tools'

    def __call__(self, subset_label=None):
        self.app._jdaviz_helper.plugins['Subset Tools'].import_region(self.input)
