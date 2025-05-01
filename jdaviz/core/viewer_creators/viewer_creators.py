from traitlets import Unicode, Bool

from jdaviz.core.events import NewViewerMessage
from jdaviz.core.template_mixin import PluginTemplateMixin, AutoTextField
from jdaviz.core.user_api import ViewerCreatorUserApi


class BaseViewerCreator(PluginTemplateMixin):
    _sidebar = 'loaders'
    _subtab = 1

    viewer_label_value = Unicode().tag(sync=True)
    viewer_label_default = Unicode().tag(sync=True)
    viewer_label_auto = Bool(True).tag(sync=True)
    viewer_label_invalid_msg = Unicode().tag(sync=True)

    def __init__(self, app, **kwargs):
        self.set_active_callback = kwargs.pop('set_active_callback', None)
        self.open_callback = kwargs.pop('open_callback', None)
        self.close_callback = kwargs.pop('close_callback', None)
        super().__init__(app, **kwargs)

        self.viewer_label = AutoTextField(self, 'viewer_label_value',
                                          'viewer_label_default',
                                          'viewer_label_auto',
                                          'viewer_label_invalid_msg')

    @property
    def user_api(self):
        return ViewerCreatorUserApi(self)

    @property
    def viewer_class(self):
        raise NotImplementedError("viewer_class must be set in subclass")

    def close_in_tray(self, close_sidebar=False):
        """
        Close the new viewer creator in the sidebar/tray.

        Parameters
        ----------
        close_sidebar : bool
            Whether to also close the sidebar itself.
        """
        if self.close_callback is not None:
            self.close_callback()
        if close_sidebar:
            self.app.state.drawer_content = ''

    def open_in_tray(self):
        """
        Show this new viewer creator in the sidebar tray.
        """
        if self.set_active_callback is None:
            raise NotImplementedError("set_active_callback must be set to open dialog to specific tab")  # noqa
        self.set_active_callback(self._registry_label)
        if self.open_callback is not None:
            self.open_callback()

    def __call__(self):
        """
        Create a viewer instance.
        """
        self.app._on_new_viewer(NewViewerMessage(self.viewer_class,
                                                 data=None,
                                                 sender=self.app),
                                vid=self.viewer_label_value, name=self.viewer_label_value)

    def vue_create_clicked(self, *args):
        self.__call__()
