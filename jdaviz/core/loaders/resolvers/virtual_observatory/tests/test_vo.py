from astropy.io import fits
from io import BytesIO
import numpy as np
import pytest
import warnings

from astropy.coordinates import SkyCoord
from astropy.table import QTable, Table
import astropy.units as u

from pyvo.dal.exceptions import DALFormatError, DALQueryError
from pyvo.io.vosi.endpoint import parse_capabilities
from pyvo.utils.vocabularies import VocabularyError
from pyvo.utils.xml.exceptions import UnknownElementWarning
from requests.exceptions import ConnectionError as RequestConnectionError

import jdaviz as jd
from jdaviz.configs.imviz.tests.utils import BaseDeconfiggedImage_WCS_WCS


class _FakeVOResults(list):
    """A mock class that simulates the results of a VO service search."""

    def to_table(self):
        return Table({'access_url': list(self)})


class _FakeVOService:
    """
    A mock class that simulates the chain of pyvo objects the VO loader
    interacts with: the registry results (``getcolumn`` and ``[short_name]``),
    the resource that returns a service (``get_service``), and the service
    itself (``search``).

    ``search`` raises ``error`` (when given) on the first call only, so that
    retry behavior can be exercised.
    """

    baseurl = "http://example.com/sia"

    def __init__(self, short_names=('FAKE',), error=None):
        self.short_names = list(short_names)
        self.error = error
        self.calls = []

    # registry results
    def getcolumn(self, name):
        return self.short_names

    def __getitem__(self, short_name):
        return self

    # resource
    def get_service(self, service_type=None):
        return self

    # service
    def search(self, coord, **kwargs):
        self.calls.append(kwargs)
        if self.error is not None and len(self.calls) == 1:
            raise self.error
        return _FakeVOResults(['a'])


# TODO: Update all _obj calls to formal API calls once Plugin API is available
class TestVODeconfiggedImageLocal(BaseDeconfiggedImage_WCS_WCS):
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
        self.helper.new_viewers['Image']()
        self.helper._app.remove_data_from_viewer("Image", "has_wcs_2")

        # Default input mode is "Source", so no viewer auto-centering yet
        vo_ldr = self.helper.loaders["virtual observatory"]._obj
        assert vo_ldr.search_input_selected == "Source"
        assert vo_ldr.source == ""

        # Switch to Viewer input mode and select the first viewer.
        # Verify coordinates have switched to the viewer center
        vo_ldr.search_input.selected = "Viewer"
        vo_ldr.viewer.selected = "Image"
        ra_str, dec_str = vo_ldr.source.split()
        np.testing.assert_allclose(
            float(ra_str), self._data_center_coords["has_wcs_1[SCI,1]"]["ra"]
        )
        np.testing.assert_allclose(
            float(dec_str), self._data_center_coords["has_wcs_1[SCI,1]"]["dec"]
        )

        # Switch to second viewer without data and verify autocoord gracefully clears source field
        vo_ldr.viewer.selected = "Image (1)"
        assert vo_ldr.source == ""

        # Coverage filtering requires a source, and the error message points at the
        # empty viewer (rather than the source field) while in Viewer input mode
        vo_ldr.resource_filter_coverage = True
        with pytest.raises(ValueError, match="Load data into viewer"):
            vo_ldr.waveband.selected = "optical"
        # clear the waveband first so that neither reset re-triggers a registry query
        vo_ldr.waveband.selected = ""
        vo_ldr.resource_filter_coverage = False

        # Now load second data into second viewer and verify coordinates
        self.helper._app.add_data_to_viewer("Image (1)", "has_wcs_2")
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
    # Use Viewer mode so that link-type changes trigger auto-centering
    vo_ldr.search_input.selected = "Viewer"
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


def test_vo_catalog_query_routes_to_query_catalog(deconfigged_helper):
    """In Catalog input mode, the VO loader's query_archive should loop over the
    catalog rows, stacking per-source results with a source_index column."""
    catalog = QTable()
    catalog['RA'] = [10.0, 20.0, 30.0] * u.deg
    catalog['Dec'] = [-5.0, 0.0, 5.0] * u.deg
    deconfigged_helper.load(catalog, format='Catalog')
    label = [d.label for d in deconfigged_helper._app.data_collection
             if d.meta.get('_importer') == 'CatalogImporter'][-1]

    vo_ldr = deconfigged_helper.loaders["virtual observatory"]._obj
    vo_ldr.search_input.selected = 'Catalog'
    vo_ldr.catalog.selected = label

    calls = []

    # Override _query_single_coord to avoid network call
    def _fake_single(coord):
        calls.append(coord)
        return Table({'access_url': ['a', 'b']})

    vo_ldr._query_single_coord = _fake_single
    vo_ldr.query_archive()

    # one query per catalog source, results stacked with source_index
    assert len(calls) == 3
    assert isinstance(calls[0], SkyCoord)
    assert len(vo_ldr._output) == 6
    assert vo_ldr._catalog_source_index_colname in vo_ldr._output.colnames
    assert sorted(set(vo_ldr._output[vo_ldr._catalog_source_index_colname])) == [0, 1, 2]


class TestVOQueryPaths:

    @pytest.fixture(autouse=True)
    def _setup(self, deconfigged_helper):
        self.vo_ldr = deconfigged_helper.loaders["virtual observatory"]._obj
        self.source = "337.5 -20.8"
        self.fake_name = 'FAKE'

    @pytest.mark.parametrize("error, expected_msg", [
        (DALFormatError(cause=RequestConnectionError("no route to host"),
                        url="http://example.com/registry"), "Can't connect to VO registry"),
        (VocabularyError("HTTP Error 403: Forbidden"), "Can't connect to VO registry"),
        (ValueError("kaboom"), "An error occurred querying the VO Registry"),
    ])
    def test_registry_query_failures_reported(self, deconfigged_helper, error, expected_msg):
        """Registry failures are both raised and reported to the user."""
        vo_ldr = self.vo_ldr

        def _raise(*constraints):
            raise error

        vo_ldr._registry_search = _raise

        with pytest.raises(type(error)):
            # setting the waveband triggers the registry query
            vo_ldr.waveband.selected = "optical"

        assert vo_ldr.resource.choices == []
        errors = [d['text'] for d in vo_ldr.query_message_items if d['color'] == 'error']
        assert len(errors) == 1 and expected_msg in errors[0]

    def test_empty_registry_results_reported(self, deconfigged_helper):
        """Check that empty registry results are reported to the user,
        and that the message is cleared once results are available again."""
        vo_ldr = self.vo_ldr
        results = _FakeVOService([self.fake_name])
        vo_ldr._registry_search = lambda *constraints: results

        vo_ldr.waveband.selected = "optical"
        assert vo_ldr.resource.choices == [self.fake_name]
        assert vo_ldr.query_message_items == []

        results.short_names = []
        vo_ldr.waveband.selected = "radio"
        assert vo_ldr.resource.choices == []
        assert [(d['text'], d['color']) for d in vo_ldr.query_message_items] == [
            (f"No {vo_ldr.waveband.selected} image resources found in the VO registry. "
             f"Try a different waveband or product type.", 'warning')]

        # with coverage filtering the registry query is source-constrained, so the
        # source is identified and clearing the filter is offered as a way out
        vo_ldr.source = self.source
        vo_ldr.resource_filter_coverage = True
        assert vo_ldr.resource.choices == []
        assert [(d['text'], d['color']) for d in vo_ldr.query_message_items] == [
            (f"No {vo_ldr.waveband.selected} image resources found in the VO registry for source: "
             f"{vo_ldr.source}. Try a different waveband or product type, or "
             f"disable coverage filtering.", 'warning')]
        vo_ldr.resource_filter_coverage = False

        # the message is cleared once the registry returns resources again
        results.short_names = [self.fake_name]
        vo_ldr.waveband.selected = "optical"
        assert vo_ldr.resource.choices == [self.fake_name]
        assert vo_ldr.query_message_items == []

    @pytest.mark.parametrize("error, n_calls, expected_error", [
        (DALQueryError("Service accepts only FORMAT = image/fits, ALL, or METADATA"), 2, None),
        # a service that doesn't accept the format argument at all
        (TypeError("search() got an unexpected keyword argument 'format'"), 2, None),
        (DALQueryError("Unsupported service protocol"), 1, "Failed to query FAKE for source"),
        (RuntimeError("service is down"), 1, "Failed to query FAKE for source"),
    ])
    def test_query_error_retried_for_format_failures(self, deconfigged_helper, error,
                                                     n_calls, expected_error):
        vo_ldr = self.vo_ldr
        vo_ldr.source = self.source
        service = _FakeVOService([self.fake_name], error=error)
        vo_ldr._full_registry_results = service
        vo_ldr.resource.choices = [self.fake_name]
        vo_ldr.resource_selected = self.fake_name

        vo_ldr.query_archive()

        assert len(service.calls) == n_calls
        # the retry drops the format argument but preserves the cone-search size
        if n_calls == 2:
            assert 'format' not in service.calls[-1]
            assert service.calls[-1]['size'] == service.calls[0]['size']
        errors = [d['text'] for d in vo_ldr.query_message_items if d['color'] == 'error']
        if expected_error is None:
            assert errors == []
            assert len(vo_ldr._output) == 1
        else:
            assert len(errors) == 1 and expected_error in errors[0]
            assert vo_ldr._output is None


class TestVOXMLInjectionWarning:
    """
    Test class for VO XML Injection warning scenarios.

    This class contains tests that demonstrate the behavior of
    UnknownElementWarning when parsing XML with non-standard elements.
    """

    @pytest.fixture(autouse=True)
    def setup_method(self):
        """
        Setup method to initialize common XML data for tests.
        """
        # XML with non-standard <limits> element
        self.xml_with_limits = b"""<?xml version="1.0" encoding="UTF-8"?>
            <capabilities xmlns="http://www.ivoa.net/xml/VOSICapabilities/v1.0"
                          xmlns:vr="http://www.ivoa.net/xml/VOResource/v1.0"
                          xmlns:tr="http://www.ivoa.net/xml/TAPRegExt/v1.0"
                          xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
              <capability standardID="ivo://ivoa.net/std/TAP" xsi:type="tr:TableAccess">
                <interface xsi:type="vr:WebService" role="std">
                  <accessURL use="base">http://example.com/tap</accessURL>
                </interface>
                <language>
                  <name>ADQL</name>
                  <version ivo-id="ivo://ivoa.net/std/ADQL#v2.0">2.0</version>
                </language>
                <outputFormat>
                  <mime>application/x-votable+xml</mime>
                </outputFormat>
                <limits>
                  <default>
                    <executionDuration>3600</executionDuration>
                    <outputLimit unit="row">10000</outputLimit>
                  </default>
                </limits>
              </capability>
            </capabilities>"""

    def test_direct_xml_parsing_triggers_warning(self):
        """Parse XML with <limits> and check the warning."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter('always')
            result = parse_capabilities(BytesIO(self.xml_with_limits))

            # Verify the warning was triggered
            limits_warnings = [
                warning for warning in w
                if issubclass(warning.category, UnknownElementWarning)
                and 'limits' in str(warning.message).lower()
            ]

            # Assert we got the warning
            assert len(limits_warnings) == 1
            assert limits_warnings[0].category == UnknownElementWarning
            assert "Unknown element limits" in str(limits_warnings[0].message)

            # Assert parsing still succeeded
            assert len(result) > 0

    @pytest.mark.filterwarnings(
        "ignore::pyvo.utils.xml.exceptions.UnknownElementWarning"
    )
    def test_xml_parsing_with_filter_passes(self):
        """
        Parse XML with <limits> WITH the warning filter decorator.

        This test should pass because the decorator filters the warning
        UnknownElementWarning, just like it sometimes does in test_coverage_toggle.
        """
        # This should NOT fail because the decorator filters the warning
        result = parse_capabilities(BytesIO(self.xml_with_limits))

        # Verify parsing succeeded and we got a result
        assert len(result) > 0


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
        vo_ldr.producttype = "Image"
        vo_ldr.search_input = "Source"
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

        # If waveband selected and coverage filtering, can't query registry
        # if we don't have a source
        expected_error_msg = "Source is required for registry querying"
        vo_ldr.resource_filter_coverage = True
        vo_ldr.source = ""
        with pytest.raises(
            ValueError,
            match=expected_error_msg,
        ):
            # Setting the waveband from nothing to something will trigger the query
            vo_ldr.waveband.selected = "optical"
        # Also verify we get a snackbar message for it, including how to resolve it
        last_msg = imviz_helper.plugins['Logger'].history[-1]["text"]
        assert expected_error_msg in last_msg
        assert "Please enter your coordinates above" in last_msg

        # If waveband selected, but NOT filtering by coverage, then allow registry query
        vo_ldr.resource_filter_coverage = False
        assert len(vo_ldr.resource.choices) > 0

    @pytest.mark.skip(reason="need to investigate failure from upstream change")
    @pytest.mark.filterwarnings(
        "ignore::pyvo.utils.xml.exceptions.UnknownElementWarning"
    )
    def test_coverage_toggle(self, imviz_helper):
        """
        Test that disabling the coverage toggle returns more available services

        NOTE: This does assume there exists at least one survey that does NOT report coverage
        within a 1-degree circle around the above-defined source position. Otherwise, returned
        resource lists will be identical.
        """
        # Set Common Args
        vo_ldr = self._init_vo_ldr_M51(imviz_helper)

        # Retrieve registry options with filtering on
        vo_ldr.resource_filter_coverage = True
        assert vo_ldr._obj.resources_loading is False
        filtered_resources = vo_ldr.resource.choices
        assert len(filtered_resources) > 0

        # Retrieve registry options with filtering off
        vo_ldr.resource_filter_coverage = False
        assert vo_ldr._obj.resources_loading is False
        nonfiltered_resources = vo_ldr.resource.choices
        # Even if the warning is triggered, this line should still pass
        # because the execution should still continue. If it doesn't,
        # then we know the warning solution did not work.
        assert len(nonfiltered_resources) > 0

        # Nonfiltered resources should be more than filtered resources
        assert len(nonfiltered_resources) > len(filtered_resources)

    def test_target_lookup_warnings(self, imviz_helper):
        """
        Tests that appropriate errors and guardrails protect the user
        when a provided source is irresolvable
        """
        # Manually set the source to a fake target
        vo_ldr = imviz_helper.loaders["virtual observatory"]
        vo_ldr.producttype = "Image"
        vo_ldr.source = "ThisIsAFakeTargetThatWontResolveToAnything"
        vo_ldr.radius = 1
        vo_ldr.radius_unit.selected = "deg"

        # If we have coverage filtering on, we should get an error.
        # The source-resolution failure is reported as itself, rather than being
        # re-wrapped as a generic registry error.
        vo_ldr.resource_filter_coverage = True
        expected_error_msg = f"Unable to resolve source coordinates: {vo_ldr.source}"
        with pytest.raises(LookupError, match=expected_error_msg):
            vo_ldr.waveband.selected = "optical"
        assert expected_error_msg in imviz_helper.plugins['Logger'].history[-1]["text"]
        assert "querying the VO Registry" not in imviz_helper.plugins['Logger'].history[-1]["text"]
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
        # Snackbar banner only, no tracebacks.
        expected_error_msg = f"Unable to resolve source name: {vo_ldr.source}"
        vo_ldr.query_archive()
        assert expected_error_msg in imviz_helper.plugins['Logger'].history[-1]["text"]

    @pytest.mark.filterwarnings("ignore:Some non-standard WCS keywords were excluded")
    @pytest.mark.filterwarnings("ignore:column .* has a unit but is kept as")
    def test_HSTM51_data_url(self, imviz_helper):
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


@pytest.mark.remote_data
class TestVOSSARemote:

    def _init_vo_loader_esossap(self):
        """
        Initialize vo loader with common test parameters

        Returns
        -------
        vo_ldr_api : VO loader user API instance
        """
        vo_loader = jd.new_app().loaders["virtual observatory"]

        # Sets common args for Remote Testing
        vo_loader.producttype = 'Spectrum'
        vo_loader.source = "NGC 5534"
        vo_loader.waveband = "optical"
        vo_loader.resource = "ESO SSAP"

        return vo_loader

    def test_esossap_data_url(self):
        """
        Test querying the ESO SSAP for spectral products
        """
        vo_loader = self._init_vo_loader_esossap()
        vo_loader.query_archive()

        # Make sure we got products
        ssa_out = vo_loader._obj._output
        assert len(ssa_out) > 0

        # Load first data product
        assert vo_loader._obj.get_selected_url() is None
        vo_loader.file_table.select_rows(0)
        assert vo_loader._obj.get_selected_url() is not None and len(vo_loader._obj.get_selected_url()) > 0  # noqa


@pytest.mark.remote_data
class TestVOSCSRemote:

    def _init_vo_loader_mastcs(self):
        """
        Initialize vo loader with common test parameters

        Returns
        -------
        vo_ldr_api : VO loader user API instance
        """
        vo_loader = jd.new_app().loaders["virtual observatory"]

        # Sets common args for Remote Testing
        vo_loader.producttype = 'Catalog'
        vo_loader.source = "M51"
        vo_loader.waveband = "optical"
        vo_loader.resource = "MAST CS"

        return vo_loader

    def test_mastcs_catalog_query(self):
        """
        Test querying the STScI MAST Cone Search for catalog targets
        """
        vo_loader = self._init_vo_loader_mastcs()
        vo_loader.query_archive()

        # Make sure we got products
        ssa_out = vo_loader._obj._output
        assert len(ssa_out) > 0
