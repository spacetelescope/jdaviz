from jdaviz.core.helpers import ConfigHelper
from jdaviz.configs.default.plugins.line_lists.line_list_mixin import LineListMixin
from jdaviz.configs.specviz import Specviz

__all__ = ['Cubeviz', 'CubeViz']


class Cubeviz(ConfigHelper, LineListMixin):
    """Cubeviz Helper class"""
    _default_configuration = 'cubeviz'

    @property
    def specviz(self):
        """
        A specviz helper (`~jdaviz.configs.specviz.Specviz`) for the Jdaviz
        application that is wrapped by cubeviz
        """
        if not hasattr(self, '_specviz'):
            self._specviz = Specviz(app=self.app)
        return self._specviz


# TODO: Officially deprecate this with coordination with JDAT notebooks team.
# For backward compatibility only.
class CubeViz(Cubeviz):
    """This class is pending deprecation. Please use `Cubeviz` instead."""
    pass
