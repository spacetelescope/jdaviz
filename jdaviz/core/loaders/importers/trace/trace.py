from specreduce.tracing import Trace


from jdaviz.core.registries import loader_importer_registry
from jdaviz.core.loaders.importers import BaseImporterToDataCollection


@loader_importer_registry('Trace')
class TraceImporter(BaseImporterToDataCollection):
    template_file = __file__, "../to_dc_with_label.vue"

    @property
    def is_valid(self):
        return (isinstance(self.input, Trace)
                and 'Spectral Extraction' in self.app._jdaviz_helper.plugins)

    @property
    def default_viewer(self):
        # returns the registry name of the default viewer
        # only used if `show_in_viewer=True` and no existing viewers can accept the data
        return 'mosviz-profile-2d-viewer'
