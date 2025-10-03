from astropy.io import fits
import numpy as np
import pytest

from jdaviz.configs.imviz.tests.utils import BaseImviz_WCS_WCS


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
        vo_ldr = self.imviz.loaders["virtual observatory"]._obj
        assert vo_ldr.viewer.selected == "Manual"
        assert vo_ldr.source == ""

        # Switch to first viewer and verify coordinates have switched
        vo_ldr.viewer.selected = "imviz-0"
        ra_str, dec_str = vo_ldr.source.split()
        np.testing.assert_allclose(
            float(ra_str), self._data_center_coords["has_wcs_1[SCI,1]"]["ra"]
        )
        np.testing.assert_allclose(
            float(dec_str), self._data_center_coords["has_wcs_1[SCI,1]"]["dec"]
        )

        # Switch to second viewer without data and verify autocoord gracefully clears source field
        vo_ldr.viewer.selected = "imviz-1"
        assert vo_ldr.source == ""

        # Now load second data into second viewer and verify coordinates
        self.imviz.app.add_data_to_viewer("imviz-1", "has_wcs_2[SCI,1]")
        ra_str, dec_str = vo_ldr.source.split()
        np.testing.assert_allclose(
            float(ra_str), self._data_center_coords["has_wcs_2[SCI,1]"]["ra"]
        )
        np.testing.assert_allclose(
            float(dec_str), self._data_center_coords["has_wcs_2[SCI,1]"]["dec"]
        )


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

    vo_ldr = imviz_helper.loaders["virtual observatory"]._obj
    vo_ldr.viewer.selected = "imviz-0"
    vo_ldr.center_on_data()
    ra_str, dec_str = vo_ldr.source.split()
    np.testing.assert_allclose(float(ra_str), 284.2101962057667)
    np.testing.assert_allclose(float(dec_str), 32.23616603681311)

    imviz_helper.plugins["Orientation"].align_by = "WCS"

    ra_str, dec_str = vo_ldr.source.split()

    # Large absolute tolerances due to WCS center coordinate bug (see issue 3225)
    # Truth values may need to be reevaluated
    np.testing.assert_allclose(float(ra_str), 239.18585, atol=30)
    np.testing.assert_allclose(float(dec_str), -9.905948925234416, atol=30)


@pytest.mark.remote_data
class TestVOImvizRemote:

    def _init_vo_ldr_M51(self, imviz_helper):
        """
        Initialize vo loader with common test parameters

        Parameters
        ----------
        imviz_helper : `~jdaviz.configs.imviz.helper`
            Instance of Imviz in which to initialize the VO loader

        Returns
        -------
        vo_ldr_api : VO loader user API instance
        """
        vo_ldr = imviz_helper.loaders["virtual observatory"]

        # Sets common args for Remote Testing
        vo_ldr.viewer.selected = "Manual"
        vo_ldr.source = "M51"
        vo_ldr.radius = 1
        vo_ldr.radius_unit.selected = "deg"
        vo_ldr.waveband.selected = "optical"

        return vo_ldr

    def test_query_registry_args(self, imviz_helper):
        """Ensure we don't query registry if we're missing required arguments"""
        # If waveband isn't selected, plugin should ignore our registry query attempts
        vo_ldr = imviz_helper.loaders["virtual observatory"]
        vo_ldr.waveband.selected = ""
        assert len(vo_ldr.resource.choices) == 0

        # If waveband selected and coverage filtering, can't query registry if don't have a source
        vo_ldr.resource_filter_coverage = True
        vo_ldr.source = ""
        with pytest.raises(
            ValueError,
            match="Source is required for registry querying when coverage filtering is enabled.",
        ):
            # Setting the waveband from nothing to something will trigger the query
            vo_ldr.waveband.selected = "optical"
            # Also verify we get a snackbar message for it
            assert any(
                "Source is required" in d["text"]
                for d in imviz_helper.plugins['Logger'].history
            )

        # If waveband selected, but NOT filtering by coverage, then allow registry query
        vo_ldr.resource_filter_coverage = False
        assert len(vo_ldr.resource.choices) > 0

    @pytest.mark.skip
    def test_coverage_toggle(self, imviz_helper):
        """
        Test that disabling the coverage toggle returns more available services

        NOTE: This does assume there exists at least one survey that does NOT report coverage
        within a 1 degree circle around the above-defined source position. Otherwise, returned
        resource lists will be identical.
        """
        # Set Common Args
        vo_ldr = self._init_vo_ldr_M51(imviz_helper)

        # Retrieve registry options with filtering on
        vo_ldr.resource_filter_coverage = True
        assert vo_ldr.resources_loading is False
        filtered_resources = vo_ldr.resource.choices
        assert len(filtered_resources) > 0

        # Retrieve registry options with filtering off
        vo_ldr.resource_filter_coverage = False
        assert vo_ldr.resources_loading is False
        nonfiltered_resources = vo_ldr.resource.choices

        # Nonfiltered resources should be more than filtered resources
        assert len(nonfiltered_resources) > len(filtered_resources)

    def test_target_lookup_warnings(self, imviz_helper):
        """
        Tests that appropriate errors and guardrails protect the user
        when a provided source is irresolvable
        """
        # Manually set the source to a fake target
        vo_ldr = imviz_helper.loaders["virtual observatory"]
        vo_ldr.source = "ThisIsAFakeTargetThatWontResolveToAnything"
        vo_ldr.radius = 1
        vo_ldr.radius_unit.selected = "deg"

        # If we have coverage filtering on, we should get an error
        vo_ldr.resource_filter_coverage = True
        expected_error_msg = "Unable to resolve source coordinates"
        with pytest.raises(LookupError, match=expected_error_msg):
            vo_ldr.waveband.selected = "optical"
            assert any(
                expected_error_msg in d["text"]
                for d in imviz_helper.plugins['Logger'].history
            )
            assert len(vo_ldr.resource.choices) == 0

        # By clearing coverage filtering, we should now be able to query the registry
        # and return the full list of available resources:
        vo_ldr.resource_filter_coverage = False
        assert len(vo_ldr.resource.choices) > 0

        # However, if we try to query a resource, we should be prevented
        # since the source still isn't resolvable.
        # Clear existing messages
        imviz_helper.plugins['Logger'].clear_history()
        vo_ldr.resource.selected = "HST.M51"
        vo_ldr.query_archive()
        assert any(
            expected_error_msg in d["text"]
            for d in imviz_helper.plugins['Logger'].history
        )

    @pytest.mark.filterwarnings("ignore::astropy.wcs.wcs.FITSFixedWarning")
    @pytest.mark.filterwarnings("ignore:Some non-standard WCS keywords were excluded")
    def test_HSTM51_data_url(self, imviz_helper):
        # Set Common Args
        vo_ldr = self._init_vo_ldr_M51(imviz_helper)

        # Select HST.M51 survey
        # Coverage not implemented for HST.M51
        vo_ldr.resource_filter_coverage = False
        assert "HST.M51" in vo_ldr.resource.choices
        vo_ldr.resource.selected = "HST.M51"
        vo_ldr.query_archive()
        assert len(vo_ldr.file_table._obj.items) > 0

        # Load first data product
        assert vo_ldr._obj.get_selected_url() is None
        vo_ldr.file_table.select_rows(0)
        assert vo_ldr._obj.get_selected_url() is not None and len(vo_ldr._obj.get_selected_url()) > 0  # noqa
