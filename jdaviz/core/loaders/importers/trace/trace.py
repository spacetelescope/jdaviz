from specreduce.tracing import Trace


from jdaviz.core.registries import loader_importer_registry
from jdaviz.core.loaders.importers import BaseImporterToPlugin


@loader_importer_registry('Trace')
class TraceImporter(BaseImporterToPlugin):
    template_file = __file__, "trace.vue"

    @property
    def is_valid(self):
        return isinstance(self.input, Trace) and self.has_default_plugin

    @property
    def default_plugin(self):
        # NOTE: eventually we'll need to differentiate between
        # cubeviz and specviz2d's spectral extraction
        return 'Spectral Extraction'

    def __call__(self, subset_label=None):
        self.app._jdaviz_helper.plugins['Spectral Extraction'].import_trace(self.input)
