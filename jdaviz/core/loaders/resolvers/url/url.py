from traitlets import Bool, Unicode, observe
from urllib.parse import urlparse

from jdaviz.core.registries import loader_resolver_registry
from jdaviz.core.loaders.resolvers import BaseResolver
from jdaviz.utils import download_uri_to_path


@loader_resolver_registry('url')
class URLResolver(BaseResolver):
    template_file = __file__, "url.vue"

    url = Unicode("").tag(sync=True)
    cache = Bool(True).tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @property
    def is_valid(self):
        return urlparse(self.url).scheme in ['http', 'https']

    @observe('url', 'cache')
    def _on_url_changed(self, change):
        self.format._update_items()

    def __call__(self, local_path=None, timeout=60):
        return download_uri_to_path(self.url, cache=self.cache,
                                    local_path=local_path, timeout=timeout)
