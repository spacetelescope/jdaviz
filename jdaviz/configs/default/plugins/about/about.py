import json

import requests
from packaging.version import Version
from traitlets import Bool, Unicode

from jdaviz.core.registries import tray_registry
from jdaviz.core.template_mixin import PluginTemplateMixin
from jdaviz.core.user_api import PluginUserApi

try:
    from jdaviz import __version__
except ImportError:  # pragma: no cover
    __version__ = "unknown"

__all__ = ['About']

# Module-level cache so the PyPI check runs at most once per process.
_pypi_version_cache = {}


@tray_registry('about', label="About",
               category='core', sidebar='popup')
class About(PluginTemplateMixin):
    """Show information about Jdaviz."""
    template_file = __file__, "about.vue"

    jdaviz_version = Unicode("unknown").tag(sync=True)
    jdaviz_pypi = Unicode("unknown").tag(sync=True)
    not_is_latest = Bool(False).tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.jdaviz_version = __version__

        # description displayed under plugin title in tray
        self._plugin_description = 'Information about Jdaviz and links to documentation and resources.'  # noqa

        if __version__ != "unknown":
            _ver_pypi = latest_version_from_pypi("jdaviz")
            if _ver_pypi:
                self.jdaviz_pypi = _ver_pypi
                self.not_is_latest = Version(__version__) < Version(_ver_pypi)
            else:  # pragma: no cover
                self.jdaviz_pypi = "unknown"
                self.not_is_latest = False

    def show_popup(self):
        self._app.force_open_about = True

    @property
    def user_api(self):
        if self.config != 'deconfigged':
            return super().user_api
        # Deconfigged needs to not show open_in_tray, but instead show_popup
        expose = ['show_popup']
        return PluginUserApi(self, expose=expose, in_tray=False)


def latest_version_from_pypi(package_name):
    """
    Return the latest version string for a package on PyPI, or ``None``.

    Results are cached per-process so repeated calls do not incur
    additional network overhead.
    """
    if package_name in _pypi_version_cache:
        return _pypi_version_cache[package_name]

    url = f'https://pypi.org/pypi/{package_name}/json'
    version = None
    try:
        r = requests.get(url, timeout=10)
    except Exception:  # nosec # pragma: no cover
        pass
    else:
        try:
            if r.ok:
                d = json.loads(r.text)
                version = d['info']['version']
        except Exception:  # nosec # pragma: no cover
            pass
        finally:
            r.close()

    _pypi_version_cache[package_name] = version
    return version
