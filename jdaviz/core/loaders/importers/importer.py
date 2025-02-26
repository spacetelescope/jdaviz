from jdaviz.core.template_mixin import PluginTemplateMixin
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
    @property
    def default_data_label(self):
        return self._registry_label

    @property
    def default_viewer(self):
        raise NotImplementedError("Importer subclass must implement default_viewer")  # noqa pragma: nocover

    @property
    def target(self):
        return self.default_viewer

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
            data_label = self.default_data_label
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
