from numpy.testing import assert_allclose
import pytest

from jdaviz.configs.imviz.tests.utils import BaseImviz_WCS_WCS
from jdaviz.configs.default.plugins.virtual_observatory.vo_plugin import vo_plugin_label


class fake_siaresult:
    """A mock class that simulates a SIAResult"""

    def __init__(self, attrs):
        for attr, value in attrs.items():
            self.__setattr__(attr, value)

    def getdataurl(self):
        return "Fake URL"


# TODO: Update all _obj calls to formal API calls once Plugin API is available
class TestVOImvizLocal(BaseImviz_WCS_WCS):
    _data_center_coords = {
        "has_wcs_1[SCI,1]": {"ra": 337.51894336761296, "dec": -20.832083054811765},
        "has_wcs_2[SCI,1]": {"ra": 337.51924057481, "dec": -20.83208305686149},
    }

    def test_autocenter_coords(self):
        """
        Loads two data products and checks the plugin correctly adjusts the automatically-derived
        coordinates of the center of the viewer when the viewer dropdown is changed.

        Also verify changing autocoord to a blank viewer with no data properly empties the source
        field.
        """
        # Create a second viewer and remove second dataset from first viewer to avoid ambiguity
        self.imviz.create_image_viewer()
        self.imviz.app.remove_data_from_viewer("imviz-0", "has_wcs_2[SCI,1]")

        # Check default viewer is "Manual"
        vo_plugin = self.imviz.plugins[vo_plugin_label]._obj
        assert vo_plugin.viewer_selected == "Manual"
        assert vo_plugin.source == ""

        # Switch to first viewer and verify coordinates have switched
        vo_plugin.viewer_selected = "imviz-0"
        ra_str, dec_str = vo_plugin.source.split()
        assert_allclose(
            float(ra_str), self._data_center_coords["has_wcs_1[SCI,1]"]["ra"]
        )
        assert_allclose(
            float(dec_str), self._data_center_coords["has_wcs_1[SCI,1]"]["dec"]
        )

        # Switch to second viewer without data and verify autocoord gracefully clears source field
        vo_plugin.viewer_selected = "imviz-1"
        assert vo_plugin.source == ""

        # Now load second data into second viewer and verify coordinates
        self.imviz.app.add_data_to_viewer("imviz-1", "has_wcs_2[SCI,1]")
        ra_str, dec_str = vo_plugin.source.split()
        assert_allclose(
            float(ra_str), self._data_center_coords["has_wcs_2[SCI,1]"]["ra"]
        )
        assert_allclose(
            float(dec_str), self._data_center_coords["has_wcs_2[SCI,1]"]["dec"]
        )

    def test_populate_table_default_headers(self):
        """
        Tests populating the results table with a mocked SIARsult
        and verifies the default headers populate the correct fields
        """
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
        """Tests the ability to control and adjust the table to custom columns"""
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

    def test_populate_table_url_header_fallback(self):
        """
        If a SIAResult is missing a required header,
        the table should switch to displaying URLs only
        """
        vo_plugin = self.imviz.plugins[vo_plugin_label]._obj
        fake_result = fake_siaresult(
            {
                "attrA": "Field A",
                "attrC": "Field C",
            }
        )

        vo_plugin._populate_table(
            [fake_result], {"Title A": "attrA", "Title B": "attrB", "Title C": "attrC"}
        )
        assert vo_plugin._populate_url_only is True
        assert vo_plugin.table.headers_visible == ["URL"]


@pytest.mark.remote_data
class TestVOImvizRemote:

    def _init_voplugin(self, imviz_helper):
        """
        Initialize the vo plugin with common test parameters

        Parameters
        ----------
        imviz_helper : `~jdaviz.configs.imviz.helper`
            Instance of Imviz in which to initialize the VO plugin

        Returns
        -------
        vo_plugin : `~jdaviz.configs.default.plugins.virtual_observatory.VoPlugin`
            The raw VoPlugin class plugin instance
        """
        vo_plugin = imviz_helper.plugins[vo_plugin_label]._obj

        # Sets common args for Remote Testing
        vo_plugin.viewer_selected = "Manual"
        vo_plugin.source = "M51"
        vo_plugin.radius = 1
        vo_plugin.waveband_selected = "optical"

        return vo_plugin

    def test_query_registry_args(self, imviz_helper):
        """Ensure we don't query registry if we're missing required arguments"""
        # If waveband isn't selected, plugin should ignore our registry query attempts
        vo_plugin = imviz_helper.plugins[vo_plugin_label]._obj
        vo_plugin.waveband_selected = ""
        vo_plugin.vue_query_registry_resources()
        assert len(vo_plugin.resources) == 0

        # If waveband selected and coverage filtering, can't query registry if don't have a source
        vo_plugin.resource_filter_coverage = True
        vo_plugin.source = ""
        with pytest.raises(
            ValueError,
            match="Source is required for registry querying when coverage filtering is enabled.",
        ):
            # Setting the waveband from nothing to something will trigger the query
            vo_plugin.waveband_selected = "optical"

        # If waveband selected, but NOT filtering by coverage, then allow registry query
        vo_plugin.resource_filter_coverage = False
        vo_plugin.vue_query_registry_resources()
        assert len(vo_plugin.resources) > 0

    def test_coverage_toggle(self, imviz_helper):
        """
        Test that disabling the coverage toggle returns more available services

        NOTE: This does assume there exists at least one survey that does NOT report coverage
        within a 1 degree circle around the above-defined source position. Otherwise the returned
        resource lists will be identical.
        """
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
        """Test the full plugin by filling out the form and loading a data product into Imviz"""
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
