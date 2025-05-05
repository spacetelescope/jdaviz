from traitlets import List

from jdaviz.core.registries import tray_registry
from jdaviz.core.template_mixin import PluginTemplateMixin
from jdaviz.core.user_api import PluginUserApi

try:
    from jdaviz import __version__
except ImportError:  # pragma: no cover
    __version__ = "unknown"

__all__ = ['Logger']


@tray_registry('logger', label="Logger",
               category='core', sidebar='info', subtab=2)
class Logger(PluginTemplateMixin):
    """Show snackbar messages in a logger UI."""
    template_file = __file__, "logger.vue"

    history = List().tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # description displayed under plugin title in tray
        self._plugin_description = 'Access history of logger messages.'

    @property
    def user_api(self):
        expose = ['history']
        return PluginUserApi(self, expose=expose)
