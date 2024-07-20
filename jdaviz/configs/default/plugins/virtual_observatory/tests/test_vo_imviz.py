import pytest

from jdaviz.configs.imviz.tests.utils import BaseImviz_WCS_WCS
from jdaviz.configs.default.plugins.virtual_observatory.vo_plugin import vo_plugin_label


# TODO: Update all _obj calls to formal API calls once Plugin API is available
class TestVOImvizLocal(BaseImviz_WCS_WCS):
    def test_autocenter_coords(self):
        # Create a second viewer and put each data in its own viewer
        self.imviz.create_image_viewer()
        self.imviz.app.remove_data_from_viewer('imviz-0','has_wcs_2[SCI,1]')
        self.imviz.app.add_data_to_viewer('imviz-1','has_wcs_2[SCI,1]')

        # Check default viewer is "Manual"
        vo_plugin = self.imviz.plugins[vo_plugin_label]._obj
        assert vo_plugin.viewer_selected == "Manual"

        # Switch to first viewer and verify coordinates have switched
        vo_plugin.viewer_selected = "imviz-0"
        assert vo_plugin.source == "337.51894336761296 -20.832083054811765"

        # Switch to second viewer and verify coordinates
        vo_plugin.viewer_selected = "imviz-1"
        assert vo_plugin.source == "337.51924057481 -20.83208305686149"


    @pytest.mark.remote_data
    def test_M32(self):
        pass
