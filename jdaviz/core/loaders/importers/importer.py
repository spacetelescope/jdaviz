from traitlets import Bool, Unicode
from glue.core.message import (DataCollectionAddMessage,
                               DataCollectionDeleteMessage)

from jdaviz.core.template_mixin import PluginTemplateMixin, AutoTextField
from jdaviz.core.user_api import ImporterUserApi

__all__ = ['BaseImporter', 'BaseImporterToDataCollection', 'BaseImporterToPlugin']


class BaseImporter(PluginTemplateMixin):
    def __init__(self, app, input, **kwargs):
        self._input = input
        super().__init__(app, **kwargs)

    @property
    def is_valid(self):
        # override by subclass
        return False  # pragma: nocover

    @property
    def input(self):
        return self._input

    @property
    def output(self):
        # override by subclass
        return self.input

    @property
    def target(self):
        raise NotImplementedError("Importer subclass must implement target")  # pragma: nocover

    def __call__(self):
        # override by subclass - should act on self.output and load into jdaviz
        raise NotImplementedError("Importer subclass must implement __call__")  # pragma: nocover

    @property
    def user_api(self):
        return ImporterUserApi(self)


class BaseImporterToDataCollection(BaseImporter):
    data_label_value = Unicode().tag(sync=True)
    data_label_default = Unicode().tag(sync=True)
    data_label_auto = Bool(True).tag(sync=True)
    data_label_invalid_msg = Unicode().tag(sync=True)

    def __init__(self, app, input, **kwargs):
        super().__init__(app, input, **kwargs)
        self.data_label_default = self._registry_label
        self.data_label = AutoTextField(self, 'data_label_value',
                                        'data_label_default',
                                        'data_label_auto',
                                        'data_label_invalid_msg')

        self.hub.subscribe(self, DataCollectionAddMessage,
                           handler=lambda _: self._on_label_changed())
        self.hub.subscribe(self, DataCollectionDeleteMessage,
                           handler=lambda _: self._on_label_changed())
        self.observe(self._on_label_changed, 'data_label_value')
        self._on_label_changed()

    @property
    def default_viewer(self):
        raise NotImplementedError("Importer subclass must implement default_viewer")  # noqa pragma: nocover

    @property
    def target(self):
        return self.default_viewer

    def _on_label_changed(self, msg={}):
        if not len(self.data_label_value.strip()):
            # strip will raise the same error for a label of all spaces
            self.data_label_invalid_msg = 'label must be provided'
            return

        # ensure the default label is unique for the data-collection
        self.data_label_default = self.app.return_unique_name(self.data_label_default)

        for data in self.app.data_collection:
            if self.data_label_value == data.label:
                self.data_label_invalid_msg = 'label already in use'
                return

        self.data_label_invalid_msg = ''

    def load_into_viewer(self, data_label):
        added = 0
        for viewer in self.app._jdaviz_helper.viewers.values():
            if data_label in viewer.data_menu.data_labels_unloaded:
                added += 1
                viewer.data_menu.add_data(data_label)
        if added == 0:
            print(f"*** will eventually create {self.default_viewer} and add data")

    def add_to_data_collection(self, data, data_label, show_in_viewer=True):
        if data_label is None:
            data_label = self.data_label_value
        self.app.add_data(data, data_label=data_label)
        if show_in_viewer:
            self.load_into_viewer(data_label)

    def __call__(self, data_label=None):
        self.add_to_data_collection(self.output, data_label, show_in_viewer=True)


class BaseImporterToPlugin(BaseImporter):
    @property
    def default_plugin(self):
        raise NotImplementedError("Importer subclass must implement default_plugin")  # noqa pragma: nocover

    @property
    def target(self):
        return self.default_plugin

    @property
    def has_default_plugin(self):
        return self.default_plugin in self.app._jdaviz_helper.plugins
