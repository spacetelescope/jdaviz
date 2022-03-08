from ipyvuetify import VuetifyTemplate
from glue.core import HubListener
from traitlets import Unicode, Bool

from jdaviz import __version__

__all__ = ['TemplateMixin', 'PluginTemplateMixin']


class TemplateMixin(VuetifyTemplate, HubListener):
    config = Unicode("").tag(sync=True)
    vdocs = Unicode("").tag(sync=True)

    def __new__(cls, *args, **kwargs):
        """
        Overload object creation so that we can inject a reference to the
        `~glue.core.hub.Hub` class before components can be initialized. This makes it so
        hub references on plugins can be passed along to components in the
        call to the initialization method.
        """
        app = kwargs.pop('app', None)
        obj = super().__new__(cls, *args, **kwargs)
        obj._app = app

        # give the vue templates access to the current config/layout
        obj.config = app.state.settings.get("configuration", "default")

        # give the vue templates access to jdaviz version
        obj.vdocs = 'latest' if 'dev' in __version__ else 'v'+__version__

        # store references to all bqplot widgets that need to handle resizing
        obj.bqplot_figs_resize = []

        return obj

    @property
    def app(self):
        """
        Allows access to the underlying Jdaviz application instance. This is
        **not** access to the helper class, but instead the
        `jdaviz.app.Application` object.
        """
        return self._app

    @property
    def hub(self):
        return self._app.session.hub

    @property
    def session(self):
        return self._app.session

    @property
    def data_collection(self):
        return self._app.session.data_collection


class PluginTemplateMixin(TemplateMixin):
    disabled_msg = Unicode("").tag(sync=True)
    plugin_opened = Bool(False).tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.app.state.add_callback('tray_items_open', self._mxn_update_plugin_opened)
        self.app.state.add_callback('drawer', self._mxn_update_plugin_opened)

    def _mxn_update_plugin_opened(self, new_value):
        app_state = self.app.state
        tray_names_open = [app_state.tray_items[i]['name'] for i in app_state.tray_items_open]
        self.plugin_opened = app_state.drawer and self._registry_name in tray_names_open
