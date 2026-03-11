from traitlets import Bool, Unicode, List, observe
from urllib.parse import urlparse
import os
from functools import cached_property

from jdaviz.core.custom_traitlets import FloatHandleEmpty
from jdaviz.core.registries import loader_resolver_registry
from jdaviz.core.loaders.resolvers import BaseResolver
from jdaviz.core.user_api import LoaderUserApi
from jdaviz.utils import download_uri_to_path, get_cloud_fits


__all__ = ['URLResolver', 'PresetURLResolver']


@loader_resolver_registry('url')
class URLResolver(BaseResolver):
    template_file = __file__, "url.vue"
    default_input = 'url'

    title = Unicode("Download from URL").tag(sync=True)
    url = Unicode("").tag(sync=True)
    url_scheme = Unicode("").tag(sync=True)
    url_not_whitelisted = Bool(False).tag(sync=True)
    url_prefix_whitelist = List([]).tag(sync=True)
    cache = Bool(True).tag(sync=True)
    local_path = Unicode("").tag(sync=True)
    timeout = FloatHandleEmpty(10).tag(sync=True)

    def __init__(self, *args, **kwargs):
        self.local_path = os.curdir
        super().__init__(*args, **kwargs)

        # Initialize whitelist from settings
        whitelist = self.app.state.settings.get('url_prefix_whitelist')
        if whitelist is not None:
            self.url_prefix_whitelist = whitelist

        # Listen for changes to app.state.settings
        self.app.state.add_callback('settings', self._on_app_settings_changed)

    def _on_app_settings_changed(self, new_settings_dict):
        """
        Re-validate URL when settings change.
        """
        # Update whitelist and re-validate the current URL
        whitelist = new_settings_dict.get('url_prefix_whitelist')
        if whitelist is not None:
            self.url_prefix_whitelist = whitelist
        else:
            self.url_prefix_whitelist = []

        if whitelist is not None and len(whitelist) > 0:
            url_stripped = self.url.strip()
            self.url_not_whitelisted = not any(
                url_stripped.startswith(prefix) for prefix in whitelist
            )
        else:
            self.url_not_whitelisted = False

    @property
    def user_api(self):
        return LoaderUserApi(self, expose=['url', 'cache', 'local_path', 'timeout'])

    @property
    def is_valid(self):
        # NOTE: if changing this, also update the object resolver to reject the same
        valid_scheme = self.url_scheme in ['http', 'https', 'mast', 'ftp', 's3']
        if not valid_scheme:
            return False

        # Check whitelist if configured
        if self.url_not_whitelisted:
            return False

        return True

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

        # Check if URL matches whitelist
        whitelist = self.app.state.settings.get('url_prefix_whitelist')
        if whitelist is not None and len(whitelist) > 0:
            url_stripped = self.url.strip()
            self.url_not_whitelisted = not any(
                url_stripped.startswith(prefix) for prefix in whitelist
            )
        else:
            self.url_not_whitelisted = False

        # Clear the cached property to force re-download
        # or otherwise read from local file cache.
        if '_uri_output_file' in self.__dict__ and change['name'] in ('url', 'cache'):
            del self._uri_output_file

        self._resolver_input_updated()

    @cached_property
    def _uri_output_file(self):
        if self.url_scheme == 's3':
            return get_cloud_fits(self.url.strip())
        return download_uri_to_path(self.url.strip(), cache=self.cache,
                                    local_path=self.local_path, timeout=self.timeout)

    def parse_input(self):
        return self._uri_output_file


class PresetURLResolver(URLResolver):
    """
    A URLResolver variant with a pre-set URL that doesn't show
    input widgets. Used for programmatically adding URLs.

    This resolver behaves like the URL resolver but hides the input fields
    by setting hide_resolver_inputs=True, while still showing query results
    and importer selection.
    """

    def __init__(self, url, title=None, *args, **kwargs):
        # Store url and title before calling parent's init
        _preset_url = url
        _preset_title = title

        # Call parent (URLResolver) init
        super().__init__(*args, **kwargs)

        # Set the url after initialization
        self.url = _preset_url

        # Set custom title if provided
        if _preset_title is not None:
            self.title = _preset_title

        # Override to hide input fields
        self.hide_resolver_inputs = True
