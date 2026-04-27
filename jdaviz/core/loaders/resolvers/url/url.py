from traitlets import Bool, Unicode, List, observe
from urllib.parse import urlparse
import os
from functools import cached_property
from pathlib import Path

from jdaviz.core.custom_traitlets import FloatHandleEmpty
from jdaviz.core.registries import loader_resolver_registry
from jdaviz.core.loaders.resolvers import BaseResolver
from jdaviz.core.user_api import LoaderUserApi
from jdaviz.utils import download_uri_to_path, get_cloud_fits, get_cloud_asdf


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
    fsspec_filesystem = None

    def __init__(self, *args, **kwargs):
        self.local_path = os.curdir
        super().__init__(*args, **kwargs)

        self.fsspec_filesystem = kwargs.get('fsspec_filesystem', None)

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
        # Call parent's method to handle server_is_remote and other settings
        super()._on_app_settings_changed(new_settings_dict)

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

    def _check_is_valid(self):
        # NOTE: if changing this, also update the object resolver to reject the same
        valid_schemes = ['http', 'https', 'mast', 'ftp', 's3']
        if self.url_scheme not in valid_schemes:
            return False, f"URI scheme must be one of {','.join(valid_schemes)}."

        # Check whitelist if configured
        if self.url_not_whitelisted:
            return False, 'URI is not whitelisted.'

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
        url_file_extension = Path(self.url.strip()).suffix.lower()  # like '.fits'
        if self.url_scheme == 's3':

            if url_file_extension in ['.fits', '.fit']:
                return get_cloud_fits(self.url.strip(), fsspec_filesystem=self.fsspec_filesystem)

            elif url_file_extension == '.asdf':
                return get_cloud_asdf(self.url.strip(), fsspec_filesystem=self.fsspec_filesystem)

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
        self._format_detection_done = False
        super().__init__(*args, **kwargs)

        # Set the URL without triggering _resolver_input_updated,
        # which would attempt an eager download and leak SSL sockets.
        # Format detection happens lazily when first needed
        # (via load() or open_in_tray()).
        with self.defer_resolver_input_updated():
            self.url = url

        if title is not None:
            self.title = title
        self.hide_resolver_inputs = True

    def _ensure_format_detection(self):
        """Trigger format detection if not yet done."""
        if not self._format_detection_done:
            self._format_detection_done = True
            self._resolver_input_updated()

    def load(self):
        """Import into jdaviz with all selected options."""
        self._ensure_format_detection()
        return super().load()

    def open_in_tray(self):
        """Show this resolver in the sidebar tray."""
        self._ensure_format_detection()
        return super().open_in_tray()
