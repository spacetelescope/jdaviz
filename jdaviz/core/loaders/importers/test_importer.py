from unittest.mock import patch

from specutils import SpectrumList
from jdaviz.core.loaders.importers.importer import BaseImporter
from jdaviz.conftest import _create_spectrum1d_with_spectral_unit


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


def test_reset_and_check_existing_data_in_dc(deconfigged_helper):
    # Can't use a premade_spectrum_list here because the flux data is duplicated
    # and so the data hashes are not unique
    spectrum_list = SpectrumList([_create_spectrum1d_with_spectral_unit(seed=i) for i in range(5)])

    test_obj = TestBaseImporter(app=deconfigged_helper.app,
                                resolver=deconfigged_helper.loaders['object']._obj,
                                input=spectrum_list)

    dh_list = test_obj.data_hashes
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
    ldr.format = '1D Spectrum List'
    ldr.importer.sources.selected = '1D Spectrum at index: 0'
    ldr.importer()

    # The data hashes update in the SpectrumList importer but are different from the
    # data hashes in our original test_obj
    dh_list = ldr.importer.sources.data_hashes
    # The obj would otherwise have all the data hashes from the SpectrumList
    test_obj.data_hashes = dh_list

    # These *should* be the same thanks to the observer on the app traitlet
    assert len(test_obj.existing_data_in_dc) == len(test_obj.app.existing_data_in_dc) == 1
    assert dh_list[0] in test_obj.existing_data_in_dc

    # Now reset again, should be the same result
    snackbar_msg = f"Selected data appears to be identical to existing data."  # noqa

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
    ldr.format = '1D Spectrum List'
    ldr.importer.sources.selected = '1D Spectrum at index: 5'
    ldr.importer()

    dh_list = ldr.importer.sources.data_hashes
    test_obj.data_hashes = dh_list

    # Although two SpectrumList objects are loaded into the data collection,
    # they share no data in common so only one value should be in existing_data_in_dc
    assert len(test_obj.existing_data_in_dc) == len(test_obj.app.existing_data_in_dc) == 1
    assert dh_list[-1] in test_obj.existing_data_in_dc

    deconfigged_helper.app.data_item_remove(test_obj.app.data_collection[1].data.label)
    # Again, existing_data_in_dc is updated from _update_existing_data_in_dc
    # in app.py, however we want to doublecheck that
    # reset_and_check_existing_data_in_dc works as expected
    assert len(test_obj.existing_data_in_dc) == len(deconfigged_helper.app.existing_data_in_dc) == 0

    test_obj.reset_and_check_existing_data_in_dc()
    assert len(test_obj.existing_data_in_dc) == len(deconfigged_helper.app.existing_data_in_dc) == 0
