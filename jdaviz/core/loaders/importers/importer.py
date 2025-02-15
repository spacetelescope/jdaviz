from jdaviz.core.template_mixin import PluginTemplateMixin
from jdaviz.core.user_api import ImporterUserApi

__all__ = ['BaseImporter']


class BaseImporter(PluginTemplateMixin):
    def __init__(self, app, input, **kwargs):
        self.input = input
        super().__init__(app, **kwargs)

    @property
    def is_valid(self):
        # override by subclass
        return False

    def __call__(self):
        # override by subclass - must convert any inputs
        # into loaded data (either in data collection or plugin)
        raise NotImplementedError("Importer subclass must implement __call__")

    @property
    def default_data_label(self):
        return self._registry_label

    @property
    def default_viewer(self):
        raise NotImplementedError("Importer subclass must implement default_viewer")

    @property
    def user_api(self):
        return ImporterUserApi(self)