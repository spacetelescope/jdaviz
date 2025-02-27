from astropy.io import fits
import numpy as np
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
        assert vo_plugin.viewer.selected == "Manual"
        assert vo_plugin.source == ""

        # Switch to first viewer and verify coordinates have switched
        vo_plugin.viewer.selected = "imviz-0"
        ra_str, dec_str = vo_plugin.source.split()
        np.testing.assert_allclose(
            float(ra_str), self._data_center_coords["has_wcs_1[SCI,1]"]["ra"]
        )
        np.testing.assert_allclose(
            float(dec_str), self._data_center_coords["has_wcs_1[SCI,1]"]["dec"]
        )

        # Switch to second viewer without data and verify autocoord gracefully clears source field
        vo_plugin.viewer.selected = "imviz-1"
        assert vo_plugin.source == ""

        # Now load second data into second viewer and verify coordinates
        self.imviz.app.add_data_to_viewer("imviz-1", "has_wcs_2[SCI,1]")
        ra_str, dec_str = vo_plugin.source.split()
        np.testing.assert_allclose(
            float(ra_str), self._data_center_coords["has_wcs_2[SCI,1]"]["ra"]
        )
        np.testing.assert_allclose(
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

    def test_populate_table_custom_headers(self):
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


def test_link_type_autocoord(imviz_helper):
    """
    Tests switching linking types forces recalculation of viewer center coordinates
    """
    # First data with WCS, same as the one in BaseImviz_WCS_NoWCS.
    hdu1 = fits.ImageHDU(np.random.rand(100, 100), name="SCI")
    hdu1.header.update(
        {
            "CTYPE1": "RA---TAN",
            "CUNIT1": "deg",
            "CDELT1": -2.777777778,
            "CRPIX1": 1,
            "CRVAL1": 337.5202808,
            "NAXIS1": 10,
            "CTYPE2": "DEC--TAN",
            "CUNIT2": "deg",
            "CDELT2": 2.777777778,
            "CRPIX2": 1,
            "CRVAL2": -20.833333059999998,
            "NAXIS2": 10,
        }
    )
    imviz_helper.load_data(hdu1, data_label="has_wcs_1")

    # Second data with WCS, similar to above but dithered by 1 pixel in X.
    hdu2 = fits.ImageHDU(np.ones((10, 10)), name="SCI")
    hdu2.header.update(
        {
            "CTYPE1": "RA---TAN",
            "CUNIT1": "deg",
            "CDELT1": -0.0002777777778,
            "CRPIX1": 2,
            "CRVAL1": 137.5202808,
            "NAXIS1": 10,
            "CTYPE2": "DEC--TAN",
            "CUNIT2": "deg",
            "CDELT2": 0.0002777777778,
            "CRPIX2": 1,
            "CRVAL2": -20.833333059999998,
            "NAXIS2": 10,
        }
    )
    imviz_helper.load_data(hdu2, data_label="has_wcs_2")

    vo_plugin = imviz_helper.plugins[vo_plugin_label]._obj
    vo_plugin.viewer.selected = "imviz-0"
    vo_plugin.center_on_data()
    ra_str, dec_str = vo_plugin.source.split()
    np.testing.assert_allclose(float(ra_str), 284.2101962057667)
    np.testing.assert_allclose(float(dec_str), 32.23616603681311)

    imviz_helper.plugins["Orientation"].align_by = "WCS"

    ra_str, dec_str = vo_plugin.source.split()

    # Large absolute tolerances due to WCS center coordinate bug (see issue 3225)
    # Truth values may need to be reevaluated
    np.testing.assert_allclose(float(ra_str), 326.7884142245305, atol=30)
    np.testing.assert_allclose(float(dec_str), -9.905948925234416, atol=30)


@pytest.mark.remote_data
class TestVOImvizRemote:

    def _init_voplugin_M51(self, imviz_helper):
        """
        Initialize vo plugin with common test parameters

        Parameters
        ----------
        imviz_helper : `~jdaviz.configs.imviz.helper`
            Instance of Imviz in which to initialize the VO plugin

        Returns
        -------
        vo_plugin_api : `~jdaviz.configs.default.plugins.virtual_observatory.VoPlugin`
            The raw VoPlugin class plugin instance
        """
        vo_plugin = imviz_helper.plugins[vo_plugin_label]._obj

        # Sets common args for Remote Testing
        vo_plugin.viewer.selected = "Manual"
        vo_plugin.source = "M51"
        vo_plugin.radius = 1
        vo_plugin.radius_unit.selected = "deg"
        vo_plugin.waveband.selected = "optical"

        return vo_plugin

    def test_query_registry_args(self, imviz_helper):
        """Ensure we don't query registry if we're missing required arguments"""
        # If waveband isn't selected, plugin should ignore our registry query attempts
        vo_plugin = imviz_helper.plugins[vo_plugin_label]._obj
        vo_plugin.waveband.selected = ""
        vo_plugin.query_registry_resources()
        assert len(vo_plugin.resource.choices) == 0

        # If waveband selected and coverage filtering, can't query registry if don't have a source
        vo_plugin.resource_filter_coverage = True
        vo_plugin.source = ""
        with pytest.raises(
            ValueError,
            match="Source is required for registry querying when coverage filtering is enabled.",
        ):
            # Setting the waveband from nothing to something will trigger the query
            vo_plugin.waveband.selected = "optical"
            # Also verify we get a snackbar message for it
            assert any(
                "Source is required" in d["text"]
                for d in imviz_helper.app.state.snackbar_history
            )

        # If waveband selected, but NOT filtering by coverage, then allow registry query
        vo_plugin.resource_filter_coverage = False
        vo_plugin.query_registry_resources()
        assert len(vo_plugin.resource.choices) > 0

    def test_coverage_toggle(self, imviz_helper):
        """
        Test that disabling the coverage toggle returns more available services

        NOTE: This does assume there exists at least one survey that does NOT report coverage
        within a 1 degree circle around the above-defined source position. Otherwise, returned
        resource lists will be identical.
        """
        # Set Common Args
        vo_plugin = self._init_voplugin_M51(imviz_helper)

        # Retrieve registry options with filtering on
        vo_plugin.resource_filter_coverage = True
        vo_plugin.query_registry_resources()
        assert vo_plugin.resources_loading is False
        filtered_resources = vo_plugin.resource.choices
        assert len(filtered_resources) > 0

        # Retrieve registry options with filtering off
        vo_plugin.resource_filter_coverage = False
        vo_plugin.query_registry_resources()
        assert vo_plugin.resources_loading is False
        nonfiltered_resources = vo_plugin.resource.choices

        # Nonfiltered resources should be more than filtered resources
        assert len(nonfiltered_resources) > len(filtered_resources)

    def test_target_lookup_warnings(self, imviz_helper):
        """
        Tests that appropriate errors and guardrails protect the user
        when a provided source is irresolvable
        """
        expected_error_msg = "Unable to resolve source coordinates"
        vo_plugin = imviz_helper.plugins[vo_plugin_label]._obj

        # Manually set the source to a fake target
        vo_plugin.viewer.selected = "Manual"
        vo_plugin.source = "ThisIsAFakeTargetThatWontResolveToAnything"
        vo_plugin.radius = 1
        vo_plugin.radius_unit.selected = "deg"

        # If we have coverage filtering on, we should get an error
        vo_plugin.resource_filter_coverage = True
        with pytest.raises(LookupError, match=expected_error_msg):
            vo_plugin.waveband.selected = "optical"
            vo_plugin.query_registry_resources()
            assert any(
                expected_error_msg in d["text"]
                for d in imviz_helper.app.state.snackbar_history
            )
            assert len(vo_plugin.resource.choices) == 0

        # By clearing coverage filtering, we should now be able to query the registry
        # and return the full list of available resources:
        vo_plugin.resource_filter_coverage = False
        vo_plugin.query_registry_resources()
        assert len(vo_plugin.resource.choices) > 0

        # However, if we try to query a resource, we should be prevented
        # since the source still isn't resolvable.
        # Clear existing messages
        imviz_helper.app.state.snackbar_history = []
        vo_plugin.resource.selected = "HST.M51"
        with pytest.raises(LookupError, match=expected_error_msg):
            vo_plugin.vue_query_resource()
            assert any(
                expected_error_msg in d["text"]
                for d in imviz_helper.app.state.snackbar_history
            )

    @pytest.mark.filterwarnings("ignore::astropy.wcs.wcs.FITSFixedWarning")
    @pytest.mark.filterwarnings("ignore:Some non-standard WCS keywords were excluded")
    def test_HSTM51_load_data(self, imviz_helper):
        """
        Tests the following:
        * The full plugin by filling out the form and loading a data product into Imviz.
        * The plugin warns user about potentially misaligned data layers
            when loading data and WCS linking is not enabled.
        * User gets properly notified when a load_data error occurs
        """
        # Set Common Args
        vo_plugin = self._init_voplugin_M51(imviz_helper)

        # Select HST.M51 survey
        # Coverage not implemented for HST.M51
        vo_plugin.resource_filter_coverage = False
        vo_plugin.query_registry_resources()
        assert "HST.M51" in vo_plugin.resource.choices
        vo_plugin.resource.selected = "HST.M51"

        # Query resource
        vo_plugin.vue_query_resource()
        assert len(vo_plugin.table.items) > 0

        # Add poisoned fake result
        fake_result = fake_siaresult(
            {
                "title": "Fake Title",
                "instr": "Fake Instrument",
                "dateobs": "Fake Dateobs",
            }
        )
        vo_plugin._populate_table([fake_result])

        # Put the fake result first to make sure we hit the fake result before the real one
        vo_plugin.table.selected_rows = [
            vo_plugin.table.items[-1],
            vo_plugin.table.items[0],
        ]
        assert vo_plugin.table.selected_rows[0]["URL"] == fake_result.getdataurl()

        # Load first data product and fake result
        vo_plugin.load_selected_data()
        assert vo_plugin.data_loading is False
        # Test that user was warned about failed file loading on fake result
        assert any(
            "Unable to load file to viewer" in d["text"]
            for d in imviz_helper.app.state.snackbar_history
        )
        # But also test that didn't prevent us from loading the valid results
        assert len(imviz_helper.app.data_collection) == 1
        assert "M51_HST.M51" in imviz_helper.data_labels[0]

        # Load second data product
        imviz_helper.app.state.snackbar_history = []  # Clear snackbar warnings
        # User should be warned about misaligned data if WCS linking isn't set
        # and there's already data in the data collection
        assert imviz_helper.plugins["Orientation"].align_by == "Pixels"
        vo_plugin.table.selected_rows = [
            vo_plugin.table.items[0]
        ]  # Select first entry
        vo_plugin.load_selected_data()
        assert vo_plugin.data_loading is False
        assert any(
            "WCS linking is not enabled; data layers may not be aligned" in d["text"]
            for d in imviz_helper.app.state.snackbar_history
        )

        # Load third data product
        imviz_helper.app.state.snackbar_history = []  # Clear snackbar warnings
        # If we switch to WCS linking, we shouldn't get a warning anymore
        # since the data will be aligned
        imviz_helper.plugins["Orientation"].align_by = "WCS"
        vo_plugin.table.selected_rows = [
            vo_plugin.table.items[0]
        ]  # Select first entry
        vo_plugin.load_selected_data()
        assert vo_plugin.data_loading is False
        assert all(
            "WCS linking is not enabled; data layers may not be aligned"
            not in d["text"]
            for d in imviz_helper.app.state.snackbar_history
        )
