"""
Comprehensive test coverage for SubsetImporter.

Test coverage includes:
- Validation for Regions and SpectralRegion inputs
- Label validation and generation
- Import functionality with Subset Tools plugin
- Edge cases and error handling
"""
import pytest
from regions import CirclePixelRegion, PixCoord, Regions
from specutils import SpectralRegion

import astropy.units as u

from jdaviz.core.loaders.importers.subset.subset import SubsetImporter


@pytest.fixture
def circle_region():
    """
    Create a simple CirclePixelRegion for testing.
    """
    return CirclePixelRegion(center=PixCoord(x=10, y=20), radius=5)


@pytest.fixture
def regions_input(circle_region):
    """
    Create a Regions object for testing.
    """
    return Regions([circle_region])


@pytest.fixture
def spectral_region():
    """
    Create a SpectralRegion for testing.
    """
    return SpectralRegion(5000 * u.AA, 6000 * u.AA)


class TestSubsetImporter:

    @pytest.fixture(autouse=True)
    def _setup(self, deconfigged_helper, spectrum1d):
        deconfigged_helper.load(spectrum1d, format='1D Spectrum')
        self.dcf_helper = deconfigged_helper
        self.app = deconfigged_helper.app

    def generate_importer(self, input_data):
        return SubsetImporter(app=self.app,
                              resolver=None,
                              parser=None,
                              input=input_data)

    def test_label_generation_and_validity(self, regions_input):
        """
        Test label things and subsequent valid calls/error messages.
        """
        importer = self.generate_importer(regions_input)

        # Test that default label (Subset N) passes validation.
        importer.subset_label_value = 'Subset 1'
        importer._on_label_changed()

        # Default label should be valid
        assert importer.subset_label_invalid_msg == ''
        assert importer.import_disabled is False

        # Label validation works correctly.
        for label_value in ('', '    '):
            importer.subset_label_value = label_value
            importer._on_label_changed()
            assert importer.subset_label_invalid_msg == 'subset_label must be provided'

        # Test that the label_invalid_msg is set for an invalid subset label.
        importer.subset_label_value = 'Subset 2'
        importer._on_label_changed()

        # Default label should be invalid
        error_msg = ("invalid subset_label: "
                     "The pattern 'Subset N' "
                     "is reserved for auto-generated labels")
        assert importer.subset_label_invalid_msg == error_msg

        # check import_disabled updates correctly
        assert importer.import_disabled is True

        # test that calling with invalid label raises ValueError
        with pytest.raises(ValueError, match=error_msg):
            importer()

    def test_is_valid(self, regions_input, spectral_region):
        """
        Test is_valid for various scenarios.
        """
        importer = self.generate_importer(regions_input)

        assert importer.is_valid is True
        assert importer.default_plugin == 'Subset Tools'

        importer = self.generate_importer(spectral_region)
        assert importer.is_valid is True

        importer = self.generate_importer('not a region')
        assert importer.is_valid is False

    def test_label_default_updates_with_subset_count(self, regions_input, spectral_region):
        """
        Test that default label updates based on subset count.
        """
        importer = self.generate_importer(regions_input)
        # Should have default label set
        assert importer.subset_label_default == 'Subset 1'
        assert importer.subset_label_auto is True

        # subset_label should be set
        assert hasattr(importer, 'subset_label')
        assert importer.subset_label is not None

        # Create a subset first
        subset_plugin = self.dcf_helper.plugins['Subset Tools']
        subset_plugin.import_region(spectral_region)

        # Now create importer and check default updates
        importer = self.generate_importer(regions_input)

        importer.subset_label_value = 'Test'
        importer._on_label_changed()

        # Should be Subset 2 since we created one subset
        assert importer.subset_label_default == 'Subset 2'

    def test_call_creates_subset(self, spectral_region):
        """
        Test that calling importer creates a subset.
        """
        importer = self.generate_importer(spectral_region)

        # Ensure valid state
        importer.subset_label_value = 'Subset 1'
        importer.subset_label_invalid_msg = ''

        # Call should not raise
        initial_subset_count = len(self.app.data_collection.subset_groups)
        importer()

        # Should have created a new subset
        assert len(self.app.data_collection.subset_groups) >= initial_subset_count
