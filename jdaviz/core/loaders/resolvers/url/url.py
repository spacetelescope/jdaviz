from traitlets import Bool, Unicode, observe
from urllib.parse import urlparse
import os

from jdaviz.core.custom_traitlets import FloatHandleEmpty
from jdaviz.core.registries import loader_resolver_registry
from jdaviz.core.loaders.resolvers import BaseResolver
from jdaviz.core.user_api import LoaderUserApi
from jdaviz.utils import download_uri_to_path

from jdaviz.core.events import SnackbarMessage

from functools import cached_property


__all__ = ['URLResolver']


@loader_resolver_registry('url')
class URLResolver(BaseResolver):
    template_file = __file__, "url.vue"
    default_input = 'url'

    url = Unicode("").tag(sync=True)
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
        return urlparse(self.url.strip()).scheme in ['http', 'https', 'mast', 'ftp']

    @observe('url', 'cache', 'timeout')
    def _on_url_changed(self, change):
        # _uri_output_file is a string to the local path which uses the same file name
        # as that from the URL. By stripping the local path, we can match to the URL.
        # We check for bool for 'cache' on/off.
        if (self._uri_output_file.lstrip(f"{self.local_path}") not in self.url.strip()
                or isinstance(change['new'], bool)):
            del self._uri_output_file

        self._update_format_items()

    @cached_property
    def _uri_output_file(self):
        return download_uri_to_path(self.url.strip(), cache=self.cache,
                                    local_path=self.local_path, timeout=self.timeout)

    def __call__(self):
        return self._uri_output_file
