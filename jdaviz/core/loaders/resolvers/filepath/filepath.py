import os

from jdaviz.core.registries import loader_resolver_registry
from jdaviz.core.template_mixin import PluginTemplateMixin


@loader_resolver_registry('filepath')
class FilepathResolver(PluginTemplateMixin):
    template_file = __file__, "filepath.vue"

    @property
    def is_valid(self):
        return os.path.exists(self.input)

    def __call__(self):
        return self.input