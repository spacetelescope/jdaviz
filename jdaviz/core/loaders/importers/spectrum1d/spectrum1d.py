from specutils import Spectrum1D

from jdaviz.core.registries import loader_importer_registry
from jdaviz.core.template_mixin import PluginTemplateMixin


@loader_importer_registry('1D Spectrum')
class Spectrum1DImporter(PluginTemplateMixin):
    template_file = __file__, "spectrum1d.vue"

    def __init__(self, app, input, **kwargs):
        # TODO: move into base class
        self.input = input
        super().__init__(app, **kwargs)

    @property
    def is_valid(self):
        return isinstance(self.input, Spectrum1D) and self.input.flux.ndim == 1

    def __call__(self):
        # TODO: move into base class
        return self.input

    @property
    def default_data_label(self):
        # TODO: move into base class
        return self._registry_label

    @property
    def default_viewer(self):
        # returns the registry name of the default viewer
        # only used if `show_in_viewer=True` and no existing viewers can accept the data
        return 'specviz-profile-viewer'