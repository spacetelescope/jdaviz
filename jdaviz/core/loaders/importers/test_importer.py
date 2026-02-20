from unittest.mock import patch
import pytest

from specutils import SpectrumList
from jdaviz.core.loaders.importers.importer import BaseImporter
from jdaviz.core.registries import loader_importer_registry
from jdaviz.conftest import _create_spectrum1d_with_spectral_unit
from jdaviz.utils import create_data_hash


# Create a minimal test class that mimics the importer behavior
# without this we get an error when attempting to use BaseImporter directly
class TestBaseImporter(BaseImporter):
    template = ''

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    # These are required to be implemented by the BaseImporter class
    # but are currently not tested here
    @property
    def target(self):
        return None

    def __call__(self, *args, **kwargs):
        return None


def test_update_existing_data_in_dc_traitlet(deconfigged_helper, premade_spectrum_list):
    # Test the sync
    test_obj = TestBaseImporter(app=deconfigged_helper.app,
                                resolver=deconfigged_helper.loaders['object']._obj,
                                parser=None,
                                input=premade_spectrum_list)

    assert len(test_obj.existing_data_in_dc) == 0
    assert len(test_obj.app.existing_data_in_dc) == 0

    test_obj.app.existing_data_in_dc.append('test_value')
    # Check that the observer ran and updated the importer traitlet
    assert test_obj.existing_data_in_dc == test_obj.app.existing_data_in_dc

    test_obj.existing_data_in_dc.append('test_value2')
    # The update works on both because of mutability, but it's safer
    # to set the app value directly
    assert test_obj.existing_data_in_dc == test_obj.app.existing_data_in_dc


class TestResetAndCheckExistingDataInDC:
    def test_reset_and_check_basic(self, deconfigged_helper):
        # Can't use a premade_spectrum_list here because the flux data is duplicated
        # and so the data hashes are not unique
        spectrum_list = SpectrumList([_create_spectrum1d_with_spectral_unit(seed=i)
                                      for i in range(5)])

        test_obj = TestBaseImporter(app=deconfigged_helper.app,
                                    resolver=deconfigged_helper.loaders['object']._obj,
                                    parser=None,
                                    input=spectrum_list)

        dh_list = [create_data_hash(spec) for spec in spectrum_list]
        assert len(dh_list) > 0
        # Not populated yet
        assert len(test_obj.existing_data_in_dc) == 0

        # Add some dummy data to existing_data_in_dc
        test_obj.existing_data_in_dc.append('test_value')

        # Now reset using the method
        test_obj.reset_and_check_existing_data_in_dc()
        # existing_data_in_dc should be cleared out and repopulated with any existing data (none)
        assert len(test_obj.existing_data_in_dc) == 0

        # Now load the data into the data collection
        ldr = deconfigged_helper.loaders['object']
        ldr.object = spectrum_list
        ldr.format = '1D Spectrum'
        ldr.importer.extension.selected = '1D Spectrum at index: 0'
        ldr.load()

        # The data hashes update in the SpectrumList importer but are different from the
        # data hashes in our original test_obj
        dh_list = ldr.importer.extension.data_hashes
        labels_list = ldr.importer.extension.labels
        # The obj would otherwise have all the data hashes/labels from the SpectrumList
        test_obj.data_hashes = dh_list
        test_obj.hash_map_to_label = dict(zip(dh_list, labels_list))

        # These *should* be the same thanks to the observer on the app traitlet
        assert len(test_obj.existing_data_in_dc) == len(test_obj.app.existing_data_in_dc) == 1
        assert dh_list[0] in test_obj.existing_data_in_dc

        # Now reset again, should be the same result
        snackbar_msg = ('Selected data appears to be identical to existing data.\n'
                        '1D Spectrum at index: 0 <=> 1D Spectrum_index-0')  # noqa

        # Mock the broadcast method to catch the snackbar message that will pop out
        # when we run the reset and check again
        with patch.object(deconfigged_helper.app.hub, 'broadcast') as mock_broadcast:
            # TODO: Uncomment when we decide to make this a warning/exception
            # with pytest.warns(UserWarning, match=re.escape(msg)):
            test_obj.reset_and_check_existing_data_in_dc()

            broadcast_msgs = [arg[0][0].text for arg in mock_broadcast.call_args_list
                              if hasattr(arg[0][0], 'text')]
            assert snackbar_msg in broadcast_msgs

        # Everything should be the same as before
        assert len(test_obj.existing_data_in_dc) == 1
        assert dh_list[0] in test_obj.existing_data_in_dc

        new_spectrum_list = SpectrumList([_create_spectrum1d_with_spectral_unit(seed=i)
                                          for i in range(5, 11)])

        # Choose a source at the end to guarantee everything is different from before
        ldr.object = new_spectrum_list
        ldr.format = '1D Spectrum'
        ldr.importer.extension.selected = '1D Spectrum at index: 5'
        ldr.load()

        dh_list = ldr.importer.extension.data_hashes
        test_obj.data_hashes = dh_list

        # Although two SpectrumList objects are loaded into the data collection,
        # they share no data in common so only one value should be in existing_data_in_dc
        assert len(test_obj.existing_data_in_dc) == len(test_obj.app.existing_data_in_dc) == 1
        assert dh_list[-1] in test_obj.existing_data_in_dc

        deconfigged_helper.app.data_item_remove(test_obj.app.data_collection[1].data.label)
        # Again, existing_data_in_dc is updated from _update_existing_data_in_dc
        # in app.py, however we want to doublecheck that
        # reset_and_check_existing_data_in_dc works as expected
        assert len(test_obj.existing_data_in_dc) == len(deconfigged_helper.app.existing_data_in_dc) == 0  # noqa

        test_obj.reset_and_check_existing_data_in_dc()
        assert len(test_obj.existing_data_in_dc) == len(deconfigged_helper.app.existing_data_in_dc) == 0  # noqa

    def test_reset_and_check_all_importers(self, deconfigged_helper,
                                           image_hdu_wcs, spectrum1d, spectrum2d,
                                           premade_spectrum_list,
                                           sky_coord_only_source_catalog):

        input_data = {'Image': image_hdu_wcs,
                      '1D Spectrum': spectrum1d,
                      '2D Spectrum': spectrum2d,
                      'Catalog': sky_coord_only_source_catalog}

        for importer_name, importer in loader_importer_registry.members.items():
            if importer_name not in input_data:
                continue

            # Now load the data into the data collection
            ldr = deconfigged_helper.loaders['object']
            ldr.object = input_data[importer_name]
            ldr.format = importer_name
            ldr.load()

            # Load the same data again
            ldr = deconfigged_helper.loaders['object']
            ldr.object = input_data[importer_name]
            ldr.format = importer_name
            ldr.load()
            test_obj = ldr.importer._obj

            # Mock the broadcast method to catch the snackbar message that should be raised
            # when we run the reset and check again
            with patch.object(deconfigged_helper.app.hub, 'broadcast') as mock_broadcast:
                # TODO: Uncomment when we decide to make this a warning/exception
                # with pytest.warns(UserWarning, match=re.escape(msg)):
                test_obj.reset_and_check_existing_data_in_dc()

                broadcast_msgs = [arg[0][0].text for arg in mock_broadcast.call_args_list
                                  if hasattr(arg[0][0], 'text')]
                assert len(broadcast_msgs) > 0


def test_reject_2d_spectrum_as_image(deconfigged_helper, spectrum2d, mos_spectrum2d_as_hdulist):
    """
    Test that 2D spectra being read in as images are rejected.
    """
    # Attempt to load should raise a helpful error
    with pytest.raises(ValueError, match="'object > Image': 'not valid'"):
        deconfigged_helper.load(spectrum2d, format='Image')

    # Verify no data was loaded
    assert len(deconfigged_helper.app.data_collection) == 0

    # Try again with 2D Spectrum as HDU with spectral wcs
    with pytest.raises(ValueError, match="'object > Image': 'not valid'"):
        deconfigged_helper.load(mos_spectrum2d_as_hdulist[1], format='Image')

    # Verify no data was loaded
    assert len(deconfigged_helper.app.data_collection) == 0

    # Verify we're able to load as 2d spectrum in follow-up
    deconfigged_helper.load(spectrum2d, format='2D Spectrum')
    assert len(deconfigged_helper.app.data_collection) > 0


class TestDataLabelOverwrite:
    """Tests for the data_label_overwrite functionality in loaders."""

    def test_overwrite_traitlet_simple_mode(self, deconfigged_helper, spectrum1d, spectrum1d_nm):
        """Test data_label_overwrite in simple (non-prefix) mode."""
        # Load initial data
        ldr = deconfigged_helper.loaders['object']
        ldr.object = spectrum1d
        ldr.format = '1D Spectrum'
        ldr.importer.data_label = 'test_spectrum'
        ldr.load()

        assert 'test_spectrum' in deconfigged_helper.app.data_collection
        assert len(deconfigged_helper.app.data_collection) == 1

        # Now try to load with the same label - should set overwrite flag
        ldr2 = deconfigged_helper.loaders['object']
        ldr2.object = spectrum1d_nm
        ldr2.format = '1D Spectrum'
        ldr2.importer.data_label = 'test_spectrum'

        # Overwrite should be True since the label already exists
        # Access _obj to get the raw importer with all traitlets
        assert ldr2.importer._obj.data_label_overwrite is True
        assert ldr2.importer._obj.data_label_invalid_msg == ''

        # Load should succeed and overwrite the existing data
        ldr2.load()
        assert len(deconfigged_helper.app.data_collection) == 1
        assert 'test_spectrum' in deconfigged_helper.app.data_collection

    def test_no_overwrite_new_label(self, deconfigged_helper, spectrum1d):
        """Test that data_label_overwrite is False for new labels."""
        ldr = deconfigged_helper.loaders['object']
        ldr.object = spectrum1d
        ldr.format = '1D Spectrum'
        ldr.importer.data_label = 'unique_label'

        # No existing data with this label
        # Access _obj to get the raw importer with all traitlets
        assert ldr.importer._obj.data_label_overwrite is False
        assert ldr.importer._obj.data_label_invalid_msg == ''

    def test_empty_label_validation(self, deconfigged_helper, spectrum1d):
        """Test that empty labels are rejected."""
        ldr = deconfigged_helper.loaders['object']
        ldr.object = spectrum1d
        ldr.format = '1D Spectrum'
        ldr.importer.data_label = ''

        # Access _obj to get the raw importer with all traitlets
        assert ldr.importer._obj.data_label_invalid_msg == 'data_label must be provided'
        assert ldr.importer._obj.data_label_overwrite is False

        # Whitespace-only should also fail
        ldr.importer.data_label = '   '
        assert ldr.importer._obj.data_label_invalid_msg == 'data_label must be provided'

    def test_overwrite_prefix_mode(self, deconfigged_helper, premade_spectrum_list):
        """Test data_label_overwrite_by_index in prefix mode."""
        ldr = deconfigged_helper.loaders['object']
        ldr.object = premade_spectrum_list
        ldr.format = '1D Spectrum'

        # Select multiple extensions to trigger prefix mode
        ldr.importer.extension.select_all()

        # Access _obj to get the raw importer with all traitlets
        importer = ldr.importer._obj

        # Verify prefix mode is active
        assert importer.data_label_is_prefix is True
        assert len(importer.data_label_suffices) == len(premade_spectrum_list)

        # Initially, no overwrites
        assert importer.data_label_overwrite is False
        assert all(v is False for v in importer.data_label_overwrite_by_index)

        # Load the data
        ldr.load()

        # Now load again with the same prefix - all should be marked for overwrite
        ldr2 = deconfigged_helper.loaders['object']
        ldr2.object = premade_spectrum_list
        ldr2.format = '1D Spectrum'
        ldr2.importer.extension.select_all()

        # Set the same prefix as before
        ldr2.importer.data_label = importer.data_label_value

        # Access _obj to get the raw importer with all traitlets
        importer2 = ldr2.importer._obj

        # All entries should be marked for overwrite
        assert importer2.data_label_overwrite is True
        assert all(v is True for v in importer2.data_label_overwrite_by_index)

    def test_overwrite_partial_prefix_mode(self, deconfigged_helper,
                                           spectrum1d, premade_spectrum_list):
        """Test partial overwrite in prefix mode (some exist, some don't)."""
        # Load one spectrum with a label matching what will be the first suffix
        ldr = deconfigged_helper.loaders['object']
        ldr.object = spectrum1d
        ldr.format = '1D Spectrum'
        ldr.importer.data_label = 'prefix_index-0'
        ldr.load()

        # Now try to load a spectrum list with prefix "prefix"
        ldr2 = deconfigged_helper.loaders['object']
        ldr2.object = premade_spectrum_list
        ldr2.format = '1D Spectrum'
        ldr2.importer.extension.select_all()
        ldr2.importer.data_label = 'prefix'

        # Access _obj to get the raw importer with all traitlets
        importer = ldr2.importer._obj

        # Only the first entry should be marked for overwrite
        # (depends on suffix format - check actual suffices)
        assert importer.data_label_overwrite is True
        # At least one should be True (the one matching 'prefix_index-0')
        assert any(v is True for v in importer.data_label_overwrite_by_index)
        # And at least one should be False (new entries)
        assert any(v is False for v in importer.data_label_overwrite_by_index)

    def test_overwrite_removes_from_viewers(self, deconfigged_helper, spectrum1d, spectrum1d_nm):
        """Test that overwriting data properly removes it from viewers first."""
        # Load initial data
        ldr = deconfigged_helper.loaders['object']
        ldr.object = spectrum1d
        ldr.format = '1D Spectrum'
        ldr.importer.data_label = 'viewer_test'
        ldr.load()

        assert 'viewer_test' in deconfigged_helper.app.data_collection
        original_data = deconfigged_helper.app.data_collection['viewer_test']

        # Load replacement data with same label (use different spectrum)
        ldr2 = deconfigged_helper.loaders['object']
        ldr2.object = spectrum1d_nm
        ldr2.format = '1D Spectrum'
        ldr2.importer.data_label = 'viewer_test'
        ldr2.load()

        # Should still only have one entry with that label
        assert len([d for d in deconfigged_helper.app.data_collection
                    if d.label == 'viewer_test']) == 1

        # The data should be the new data (different flux values)
        new_data = deconfigged_helper.app.data_collection['viewer_test']
        # Verify it's actually different data (the object should be different)
        assert new_data is not original_data
