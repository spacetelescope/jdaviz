from specreduce.tracing import Trace


from jdaviz.core.registries import loader_importer_registry
from jdaviz.core.loaders.importers import BaseImporterToDataCollection


@loader_importer_registry('Trace')
class TraceImporter(BaseImporterToDataCollection):
    template_file = __file__, "../to_dc_with_label.vue"

    @property
    def is_valid(self):
        if self.app.config not in ('deconfigged', 'specviz2d'):
            # NOTE: temporary during deconfig process
            return False
        return (isinstance(self.input, Trace)
                and 'Spectral Extraction' in self.app._jdaviz_helper.plugins)

    @property
    def default_viewer_reference(self):
        # returns the registry name of the default viewer
        # only used if `show_in_viewer=True` and no existing viewers can accept the data
        return 'spectrum-2d-viewer'
