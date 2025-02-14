from specutils import Spectrum1D

from jdaviz.core.registries import loader_importer_registry
from jdaviz.core.template_mixin import PluginTemplateMixin


@loader_importer_registry('1D Spectrum')
class Spectrum1DImporter(PluginTemplateMixin):
    template_file = __file__, "spectrum1d.vue"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @property
    def is_valid(self):
        return isinstance(self.input, Spectrum1D) and self.input.flux.ndim == 1

    def __call__(self):
        return self.input
