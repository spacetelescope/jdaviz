from specreduce.tracing import Trace


from jdaviz.core.registries import loader_importer_registry
from jdaviz.core.loaders.importers import BaseImporterToDataCollection


@loader_importer_registry('Trace')
class TraceImporter(BaseImporterToDataCollection):
    template_file = __file__, "../to_dc_with_label.vue"

    @staticmethod
    def _get_supported_viewers():
        return [{'label': '2D Spectrum', 'reference': 'spectrum-2d-viewer'}]

    @property
    def is_valid(self):
        if self.app.config not in ('deconfigged', 'specviz2d'):
            # NOTE: temporary during deconfig process
            return False
        return (isinstance(self.input, Trace)
                and 'Spectral Extraction' in self.app._jdaviz_helper.plugins)
