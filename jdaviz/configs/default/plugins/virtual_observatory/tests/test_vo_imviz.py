import pytest

from jdaviz.configs.imviz.tests.utils import BaseImviz_WCS_WCS
from jdaviz.configs.default.plugins.virtual_observatory.vo_plugin import vo_plugin_label


class fake_siaresult:
    def __init__(self, attrs):
        for attr, value in attrs.items():
            self.__setattr__(attr, value)

    def getdataurl(self):
        return "Fake URL"


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
        vo_plugin = self.imviz.plugins[vo_plugin_label]._obj
        fake_result = fake_siaresult(
            {
                "title": "Fake Title",
                "instr": "Fake Instrument",
                "dateobs": "Fake Dateobs",
            }
        )
        vo_plugin._populate_table([fake_result])

        assert vo_plugin.table.items == [
            {
                "URL": fake_result.getdataurl(),
                "Title": fake_result.title,
                "Instrument": fake_result.instr,
                "DateObs": fake_result.dateobs,
            }
        ]

    def test_populate_table_customm_headers(self):
        vo_plugin = self.imviz.plugins[vo_plugin_label]._obj
        fake_result = fake_siaresult(
            {
                "attrA": "Field A",
                "attrB": "Field B",
                "attrC": "Field C",
            }
        )
        vo_plugin._populate_table(
            [fake_result], {"Title A": "attrA", "Title B": "attrB", "Title C": "attrC"}
        )

        assert vo_plugin.table.items == [
            {
                "URL": fake_result.getdataurl(),
                "Title A": fake_result.attrA,
                "Title B": fake_result.attrB,
                "Title C": fake_result.attrC,
            }
        ]


@pytest.mark.remote_data
class TestVOImvizRemote:

    def _init_voplugin(self, imviz_helper):
        vo_plugin = imviz_helper.plugins[vo_plugin_label]._obj

        # Sets common args for Remote Testing
        vo_plugin.viewer_selected = "Manual"
        vo_plugin.source = "M51"
        vo_plugin.waveband_selected = "optical"

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

    @pytest.mark.filterwarnings("ignore::astropy.wcs.wcs.FITSFixedWarning")
    @pytest.mark.filterwarnings("ignore:Some non-standard WCS keywords were excluded")
    def test_HSTM51_load_data(self, imviz_helper):
        # Set Common Args
        vo_plugin = self._init_voplugin(imviz_helper)

        # Select HST.M51 survey
        # Coverage not implemented for HST.M51
        vo_plugin.resource_filter_coverage = False
        vo_plugin.vue_query_registry_resources()
        assert "HST.M51" in vo_plugin.resources
        vo_plugin.resource_selected = "HST.M51"

        # Query resource
        vo_plugin.vue_query_resource()
        assert len(vo_plugin.table.items) > 0

        # Load first data product:
        vo_plugin.table.selected_rows = [vo_plugin.table.items[0]]  # Select first entry
        vo_plugin.vue_load_selected_data()
        assert len(imviz_helper.app.data_collection) == 1
        assert "M51_HST.M51" in imviz_helper.data_labels[0]
