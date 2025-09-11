from astropy.table import QTable

from jdaviz.core.registries import loader_importer_registry
from jdaviz.core.loaders.importers import BaseImporterToDataCollection


__all__ = ['ScatterImporter']


@loader_importer_registry('Scatter')
class ScatterImporter(BaseImporterToDataCollection):
    template_file = __file__, "../to_dc_with_label.vue"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.data_label_default = 'Data'

    @property
    def is_valid(self):
        if self.app.config not in ('deconfigged',):
            # NOTE: temporary during deconfig process
            return False
        return isinstance(self.input, QTable)

    @staticmethod
    def _get_supported_viewers():
        return [{'label': 'Scatter', 'reference': 'scatter-viewer'}]
