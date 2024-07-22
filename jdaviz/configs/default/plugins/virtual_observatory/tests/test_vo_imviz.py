import pytest

from jdaviz.configs.imviz.tests.utils import BaseImviz_WCS_WCS
from jdaviz.configs.default.plugins.virtual_observatory.vo_plugin import vo_plugin_label


# TODO: Update all _obj calls to formal API calls once Plugin API is available
class TestVOImvizLocal(BaseImviz_WCS_WCS):
    def test_autocenter_coords(self):
        # Create a second viewer and put each data in its own viewer
        self.imviz.create_image_viewer()
        self.imviz.app.remove_data_from_viewer("imviz-0", "has_wcs_2[SCI,1]")
        self.imviz.app.add_data_to_viewer("imviz-1", "has_wcs_2[SCI,1]")

        # Check default viewer is "Manual"
        vo_plugin = self.imviz.plugins[vo_plugin_label]._obj
        assert vo_plugin.viewer_selected == "Manual"

        # Switch to first viewer and verify coordinates have switched
        vo_plugin.viewer_selected = "imviz-0"
        assert vo_plugin.source == "337.51894336761296 -20.832083054811765"

        # Switch to second viewer and verify coordinates
        vo_plugin.viewer_selected = "imviz-1"
        assert vo_plugin.source == "337.51924057481 -20.83208305686149"

    def test_populate_table_default_headers(self):
        class fake_siaresult:
            def __init__(self):
                self.title = "Fake Title"
                self.instr = "Fake Instrument"
                self.dateobs = "Fake Dateobs"

            def getdataurl(self):
                return "Fake URL"

        vo_plugin = self.imviz.plugins[vo_plugin_label]._obj
        fake_result = fake_siaresult()
        vo_plugin._populate_table([fake_result])

        assert vo_plugin.table.items == [
            {
                "URL": fake_result.getdataurl(),
                "Title": fake_result.title,
                "Instrument": fake_result.instr,
                "DateObs": fake_result.dateobs,
            }
        ]


@pytest.mark.remote_data
class TestVOImvizRemote:

    def _init_voplugin(self, imviz_helper):
        vo_plugin = imviz_helper.plugins[vo_plugin_label]._obj

        # Sets common args for Remote Testing
        vo_plugin.viewer_selected = "Manual"
        vo_plugin.source = "M32"
        vo_plugin.waveband_selected = "infrared"

        return vo_plugin

    def test_coverage_toggle(self, imviz_helper):
        # Set Common Args
        vo_plugin = self._init_voplugin(imviz_helper)

        # Retrieve registry options with filtering on
        vo_plugin.resource_filter_coverage = True
        vo_plugin.vue_query_registry_resources()
        filtered_resources = vo_plugin.resources
        assert len(filtered_resources) > 0

        # Retrieve registry options with filtering off
        vo_plugin.resource_filter_coverage = False
        vo_plugin.vue_query_registry_resources()
        nonfiltered_resources = vo_plugin.resources

        # Nonfiltered resources should be more than filtered resources
        assert len(nonfiltered_resources) > len(filtered_resources)
