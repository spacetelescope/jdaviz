from glue.config import viewer_tool

from jdaviz.configs.mosviz.plugins.tools import MosvizHomeZoom
from jdaviz.configs.specviz.plugins.viewers import Spectrum1DViewer, Spectrum2DViewer


@viewer_tool
class MatchedHomeZoom(MosvizHomeZoom):
    tool_id = 'deconf:homezoom_matchx'

    def is_visible(self):
        return True

    def _is_matched_viewer(self, viewer):
        return isinstance(viewer, (Spectrum1DViewer, Spectrum2DViewer))
