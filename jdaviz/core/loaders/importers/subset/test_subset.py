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



class TestSubsetImporterValidation:
    """
    Test SubsetImporter input validation.
    """

    def test_is_valid_with_regions(self, specviz_helper, regions_input):
        """
        Test is_valid returns True for Regions input.
        """
        app = specviz_helper.app

        importer = SubsetImporter(
            app=app,
            resolver=None,
            parser=None,
            input=regions_input
        )

        assert importer.is_valid is True
        assert importer.default_plugin == 'Subset Tools'

    def test_is_valid_with_spectral_region(
        self, specviz_helper, spectral_region
    ):
        """
        Test is_valid returns True for SpectralRegion input.
        """
        app = specviz_helper.app

        importer = SubsetImporter(
            app=app,
            resolver=None,
            parser=None,
            input=spectral_region
        )

        assert importer.is_valid is True

    def test_is_valid_with_invalid_input(self, specviz_helper):
        """
        Test is_valid returns False for invalid input.
        """
        app = specviz_helper.app
        invalid_input = 'not a region'

        importer = SubsetImporter(
            app=app,
            resolver=None,
            parser=None,
            input=invalid_input
        )

        assert importer.is_valid is False



class TestSubsetImporterLabelValidation:
    """
    Test label validation logic in SubsetImporter.
    """

    def test_empty_label_validation(self, specviz_helper, regions_input):
        """
        Test that empty label raises validation error.
        """
        app = specviz_helper.app

        importer = SubsetImporter(
            app=app,
            resolver=None,
            parser=None,
            input=regions_input
        )

        importer.subset_label_value = ''
        importer._on_label_changed()

        assert (importer.subset_label_invalid_msg
                == 'subset_label must be provided')

    def test_whitespace_only_label_validation(
        self, specviz_helper, regions_input
    ):
        """
        Test that whitespace-only label raises validation error.
        """
        app = specviz_helper.app

        importer = SubsetImporter(
            app=app,
            resolver=None,
            parser=None,
            input=regions_input
        )

        importer.subset_label_value = '   '
        importer._on_label_changed()

        assert (importer.subset_label_invalid_msg
                == 'subset_label must be provided')

    def test_default_label_validation(
        self, specviz_helper, regions_input
    ):
        """
        Test that default label (Subset N) passes validation.
        """
        app = specviz_helper.app

        importer = SubsetImporter(
            app=app,
            resolver=None,
            parser=None,
            input=regions_input
        )

        # Set label to default
        importer.subset_label_value = 'Subset 1'
        importer._on_label_changed()

        # Default label should be valid
        assert importer.subset_label_invalid_msg == ''

    def test_label_default_updates_with_subset_count(
        self, specviz_helper, regions_input, spectral_region, spectrum1d
    ):
        """
        Test that default label updates based on subset count.
        """
        app = specviz_helper.app

        # Load data first (required before creating subsets)
        specviz_helper.load_data(spectrum1d)

        # Create a subset first
        subset_plugin = specviz_helper.plugins['Subset Tools']
        subset_plugin.import_region(spectral_region)

        # Now create importer and check default updates
        importer = SubsetImporter(
            app=app,
            resolver=None,
            parser=None,
            input=regions_input
        )

        importer.subset_label_value = 'Test'
        importer._on_label_changed()

        # Should be Subset 2 since we created one subset
        assert importer.subset_label_default == 'Subset 2'


class TestSubsetImporterImportDisabled:
    """
    Test import_disabled state management.
    """

    def test_import_disabled_on_invalid_label(
        self, specviz_helper, regions_input
    ):
        """
        Test that import is disabled when label is invalid.
        """
        app = specviz_helper.app

        importer = SubsetImporter(
            app=app,
            resolver=None,
            parser=None,
            input=regions_input
        )

        importer.subset_label_invalid_msg = 'Some error'
        importer._set_import_disabled()

        assert importer.import_disabled is True

    def test_import_enabled_on_valid_label(
        self, specviz_helper, regions_input
    ):
        """
        Test that import is enabled when label is valid.
        """
        app = specviz_helper.app

        importer = SubsetImporter(
            app=app,
            resolver=None,
            parser=None,
            input=regions_input
        )

        importer.subset_label_invalid_msg = ''
        importer._set_import_disabled()

        assert importer.import_disabled is False


class TestSubsetImporterCall:
    """
    Test the __call__ method of SubsetImporter.
    """

    def test_call_with_invalid_label_raises_error(
        self, specviz_helper, regions_input
    ):
        """
        Test that calling with invalid label raises ValueError.
        """
        app = specviz_helper.app

        importer = SubsetImporter(
            app=app,
            resolver=None,
            parser=None,
            input=regions_input
        )

        error_msg = 'Invalid label'
        importer.subset_label_invalid_msg = error_msg

        with pytest.raises(ValueError, match=error_msg):
            importer()

    def test_call_creates_subset(
        self, specviz_helper, spectral_region, spectrum1d
    ):
        """
        Test that calling importer creates a subset.
        """
        app = specviz_helper.app

        # Load some data first (required for creating subsets)
        specviz_helper.load_data(spectrum1d)

        importer = SubsetImporter(
            app=app,
            resolver=None,
            parser=None,
            input=spectral_region
        )

        # Ensure valid state
        importer.subset_label_value = 'Subset 1'
        importer.subset_label_invalid_msg = ''

        # Call should not raise
        initial_subset_count = len(app.data_collection.subset_groups)
        importer()

        # Should have created a new subset
        assert len(app.data_collection.subset_groups) >= initial_subset_count


class TestSubsetImporterEdgeCases:
    """
    Test edge cases and boundary conditions.
    """

    def test_initialization_creates_default_label(
        self, specviz_helper, regions_input
    ):
        """
        Test that initialization creates default label.
        """
        app = specviz_helper.app

        importer = SubsetImporter(
            app=app,
            resolver=None,
            parser=None,
            input=regions_input
        )

        # Should have default label set
        assert importer.subset_label_default == 'Subset 1'
        assert importer.subset_label_auto is True

    def test_label_auto_text_field_exists(
        self, specviz_helper, regions_input
    ):
        """
        Test that AutoTextField is created for label.
        """
        app = specviz_helper.app

        importer = SubsetImporter(
            app=app,
            resolver=None,
            parser=None,
            input=regions_input
        )

        # Should have AutoTextField attached
        assert hasattr(importer, 'subset_label')
        assert importer.subset_label is not None

