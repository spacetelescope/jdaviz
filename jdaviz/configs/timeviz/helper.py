from jdaviz.core.helpers import ConfigHelper

__all__ = ['Timeviz']


class Timeviz(ConfigHelper):
    """Timeviz Helper class."""
    _default_configuration = 'timeviz'

    def show(self):
        self.app
