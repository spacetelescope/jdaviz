from traitlets import List, Unicode

from jdaviz.core.registries import tray_registry
from jdaviz.core.template_mixin import PluginTemplateMixin, SelectPluginComponent
from jdaviz.core.user_api import PluginUserApi

try:
    from jdaviz import __version__
except ImportError:  # pragma: no cover
    __version__ = "unknown"

__all__ = ['Logger', '_verbosity_levels']

_verbosity_levels = ('debug', 'info', 'warning', 'error')


@tray_registry('logger', label="Logger",
               category='core', sidebar='info', subtab=2)
class Logger(PluginTemplateMixin):
    """Show snackbar messages in a logger UI."""
    template_file = __file__, "logger.vue"

    popup_verbosity_items = List().tag(sync=True)
    popup_verbosity_selected = Unicode('warning').tag(sync=True)
    history_verbosity_items = List().tag(sync=True)
    history_verbosity_selected = Unicode('info').tag(sync=True)

    history = List().tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # description displayed under plugin title in tray
        self._plugin_description = 'Access history of logger messages.'

        self.popup_verbosity = SelectPluginComponent(self,
                                                     items='popup_verbosity_items',
                                                     selected='popup_verbosity_selected',
                                                     manual_options=_verbosity_levels)

        self.history_verbosity = SelectPluginComponent(self,
                                                       items='history_verbosity_items',
                                                       selected='history_verbosity_selected',
                                                       manual_options=_verbosity_levels)

    @property
    def user_api(self):
        expose = ['popup_verbosity', 'history_verbosity', 'history', 'clear_history']
        return PluginUserApi(self, expose=expose)

    def clear_history(self):
        self.history = []

    def vue_clear_history(self, *args):
        return self.clear_history()

    def queue_message(self, msg, msg_level=None):
        if msg_level not in _verbosity_levels:
            msg_level = 'info'

        msg_level = _verbosity_levels.index(msg_level)
        history_level = _verbosity_levels.index(self.history_verbosity_selected)
        popup_level = _verbosity_levels.index(self.popup_verbosity_selected)

        self.app.state.snackbar_queue.put(self.app.state, self,
                                          msg,
                                          history=msg_level >= history_level,
                                          popup=msg_level >= popup_level)
