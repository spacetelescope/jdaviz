from specreduce.tracing import Trace


from jdaviz.core.registries import loader_importer_registry
from jdaviz.core.loaders.importers import BaseImporterToDataCollection


@loader_importer_registry('Trace')
class TraceImporter(BaseImporterToDataCollection):
    template_file = __file__, "../to_dc_with_label.vue"

    @staticmethod
    def _get_supported_viewers():
        return [{'label': '2D Spectrum', 'reference': 'spectrum-2d-viewer'}]

    def _check_is_valid(self):
        if self._app.config not in ('deconfigged', 'specviz2d'):
            # NOTE: temporary during deconfig process
            return 'Trace importer is only supported in specviz2d, generalized jdaviz.'

        if not isinstance(self.input, Trace):
            return 'Input is not a Trace.'

        if 'Spectral Extraction' not in self._app._jdaviz_helper.plugins:
            return 'Spectral Extraction plugin (for Trace) not available.'

        return ''
