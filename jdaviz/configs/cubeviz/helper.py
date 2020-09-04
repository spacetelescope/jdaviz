from jdaviz.core.helpers import ConfigHelper
from ..default.plugins.line_lists.line_list_mixin import LineListMixin


class CubeViz(ConfigHelper, LineListMixin):
    """CubeViz Helper class"""
    _default_configuration = 'cubeviz'
