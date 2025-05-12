from traitlets import Unicode, Bool, observe

from jdaviz.core.events import NewViewerMessage
from jdaviz.core.template_mixin import (PluginTemplateMixin, AutoTextField,
                                        DatasetMultiSelectMixin, ViewerSelectMixin)
from jdaviz.core.user_api import ViewerCreatorUserApi


class BaseViewerCreator(PluginTemplateMixin, DatasetMultiSelectMixin, ViewerSelectMixin):
    _sidebar = 'loaders'
    _subtab = 1

    viewer_type = Unicode().tag(sync=True)
    is_relevant = Bool(False).tag(sync=True)

    viewer_label_value = Unicode().tag(sync=True)
    viewer_label_default = Unicode().tag(sync=True)
    viewer_label_auto = Bool(True).tag(sync=True)
    viewer_label_invalid_msg = Unicode().tag(sync=True)

    def __init__(self, app, **kwargs):
        self.set_active_callback = kwargs.pop('set_active_callback', None)
        self.open_callback = kwargs.pop('open_callback', None)
        self.close_callback = kwargs.pop('close_callback', None)
        super().__init__(app, **kwargs)
        self.dataset.multiselect = True
        self.viewer_type = self._registry_label

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

    @observe('dataset_items')
    def _dataset_items_changed(self, *args):
        self._set_is_relevant()

    def _set_is_relevant(self):
        if len(self.dataset_items):
            self.is_relevant = True
        else:
            self.is_relevant = False

    @observe('is_relevant')
    def _is_relevant_changed(self, *args):
        labels = [ti['label'] for ti in self.app.state.new_viewer_items]
        if self._registry_label not in labels:
            return
        index = labels.index(self._registry_label)
        self.app.state.new_viewer_items[index]['is_relevant'] = self.is_relevant

    @observe('viewer_label_value', 'viewer_items')
    def _viewer_label_value_changed(self, *args):
        # forbid using an existing viewer label
        if self.viewer_label_value in self.viewer.choices:
            self.viewer_label_invalid_msg = f"Viewer label '{self.viewer_label_value}' already in use."  # noqa
        else:
            self.viewer_label_invalid_msg = ''

    @observe('viewer_items')
    def _viewer_items_changed(self, *args):
        if self.viewer_label_default in self.viewer.choices:
            self.viewer_label_default = self.app.return_unique_name(self.viewer_label_default, 'viewer')  # noqa

    def __call__(self):
        """
        Create a viewer instance.
        """
        if self.viewer_label_invalid_msg:
            raise ValueError(self.viewer_label_invalid_msg)
        nv = self.app._on_new_viewer(NewViewerMessage(self.viewer_class,
                                                      data=None,
                                                      sender=self.app),
                                     vid=self.viewer_label_value, name=self.viewer_label_value)
        dm = nv.data_menu
        for dataset in self.dataset.selected:
            dm.add_data(dataset)
        return nv.user_api

    def vue_create_clicked(self, *args):
        self.__call__()
