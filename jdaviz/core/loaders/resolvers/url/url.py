from traitlets import Bool, Unicode, observe
from urllib.parse import urlparse
import os
from functools import cached_property

from jdaviz.core.custom_traitlets import FloatHandleEmpty
from jdaviz.core.registries import loader_resolver_registry
from jdaviz.core.loaders.resolvers import BaseResolver
from jdaviz.core.user_api import LoaderUserApi
from jdaviz.utils import download_uri_to_path, get_cloud_fits


__all__ = ['URLResolver']


@loader_resolver_registry('url')
class URLResolver(BaseResolver):
    template_file = __file__, "url.vue"
    default_input = 'url'

    url = Unicode("").tag(sync=True)
    url_scheme = Unicode("").tag(sync=True)
    cache = Bool(True).tag(sync=True)
    local_path = Unicode("").tag(sync=True)
    timeout = FloatHandleEmpty(10).tag(sync=True)

    def __init__(self, *args, **kwargs):
        self.local_path = os.curdir
        super().__init__(*args, **kwargs)

    @property
    def user_api(self):
        return LoaderUserApi(self, expose=['url', 'cache', 'local_path', 'timeout'])

    @property
    def is_valid(self):
        return self.url_scheme in ['http', 'https', 'mast', 'ftp', 's3']

    @property
    def default_label(self):
        # Use the last part of the URL as the default label, if available.
        # Otherwise, return None.
        if self.url.strip():
            return os.path.splitext(os.path.basename(self.url.strip()))[0]
        return None

    @observe('url', 'cache', 'timeout')
    def _on_url_changed(self, change):
        self.url_scheme = urlparse(self.url.strip()).scheme

        # Clear the cached property to force re-download
        # or otherwise read from local file cache.
        if '_uri_output_file' in self.__dict__ and change['name'] in ('url', 'cache'):
            del self._uri_output_file

        self._update_format_items()

    @cached_property
    def _uri_output_file(self):
        if self.url_scheme == 's3':
            return get_cloud_fits(self.url.strip())
        return download_uri_to_path(self.url.strip(), cache=self.cache,
                                    local_path=self.local_path, timeout=self.timeout)

    def __call__(self):
        return self._uri_output_file
