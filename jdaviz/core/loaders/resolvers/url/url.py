import os
from traitlets import Unicode

from jdaviz.core.registries import loader_resolver_registry
from jdaviz.core.template_mixin import PluginTemplateMixin
from jdaviz.utils import download_uri_to_path


@loader_resolver_registry('url')
class URLResolver(PluginTemplateMixin):
    template_file = __file__, "url.vue"

    url = Unicode("").tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @property
    def is_valid(self):
        return not os.path.exists(self.url)

    def __call__(self, cache=True, local_path=None, timeout=60):
        return download_uri_to_path(self.url, cache=cache,
                                    local_path=local_path, timeout=timeout)
