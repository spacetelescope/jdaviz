from jdaviz.core.helpers import ConfigHelper
from jdaviz.configs.default.plugins.line_lists.line_list_mixin import LineListMixin


class App(ConfigHelper, LineListMixin):
    """Base user-facing application helper."""

    _default_configuration = "deconfigged"  # temporary during deconfig process

    def __init__(self, *args, **kwargs):
        api_hints_obj = kwargs.pop('api_hints_obj', 'viz')
        super().__init__(*args, **kwargs)
        self.app.api_hints_obj = api_hints_obj

        # Temporary during deconfig process
        self.load = self._load
        self.app.state.dev_loaders = True
