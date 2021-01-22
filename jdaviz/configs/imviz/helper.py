from jdaviz.core.helpers import ConfigHelper

__all__ = ['Imviz']


class Imviz(ConfigHelper):
    """Imviz helper class."""

    _default_configuration = "imviz"

    def show(self):
        self.app
