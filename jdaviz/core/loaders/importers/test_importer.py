import pytest
from unittest.mock import patch
import re

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

    test_obj.app.existing_data_in_dc['test_key'] = 'test_value'
    # Check that the observer ran and updated the importer traitlet
    assert test_obj.existing_data_in_dc == test_obj.app.existing_data_in_dc


def test_reset_and_check_existing_data_in_dc(deconfigged_helper):
    # Can't use a premade_spectrum_list here because the flux data is duplicated
    # and so the data hashes are not unique
    spectrum_list = SpectrumList([_create_spectrum1d_with_spectral_unit(seed=i) for i in range(5)])

    # Test the reset and check methods
    test_obj = TestBaseImporter(app=deconfigged_helper.app,
                                resolver=deconfigged_helper.loaders['object']._obj,
                                input=spectrum_list)

    dh_list = test_obj.data_hashes
    assert len(dh_list) > 0
    # No reset and not populated yet
    assert len(test_obj.existing_data_in_dc) == 0

    # Add some dummy data to existing_data_in_dc
    test_obj.existing_data_in_dc['test_key'] = 'test_value'

    # Now reset using the method
    test_obj.reset_and_check_existing_data_in_dc()
    assert len(test_obj.existing_data_in_dc) == len(dh_list)
    # All values should be false since nothing is in the data collection yet
    assert sum(test_obj.existing_data_in_dc.values()) == 0

    # Now load the data into the data collection, defaults to loading the first source
    deconfigged_helper.load(spectrum_list, format='1D Spectrum List')
    # The data hashes update in the SpectrumList importer but are different from the
    # data hashes in our original test_obj
    dh_list = list(test_obj.existing_data_in_dc.keys())
    test_obj.data_hashes = list(test_obj.existing_data_in_dc.keys())

    # This should happen due to `_update_existing_data_in_dc` in app
    assert len(test_obj.existing_data_in_dc) == len(spectrum_list)
    assert sum(test_obj.existing_data_in_dc.values()) == 1
    assert test_obj.existing_data_in_dc[dh_list[0]] is True

    # Now reset again, should be the same result
    test_obj.reset_and_check_existing_data_in_dc()
    assert len(test_obj.existing_data_in_dc) == len(spectrum_list)
    assert test_obj.existing_data_in_dc[dh_list[0]] is True
    assert all(v is False for k, v in test_obj.existing_data_in_dc.items() if k != dh_list[0])

    new_spectrum_list = SpectrumList([_create_spectrum1d_with_spectral_unit(seed=i)
                                      for i in range(5, 11)])

    # Load single source by default
    # Choose a source at the end to guarantee everything is different from before
    deconfigged_helper.load(new_spectrum_list,
                            format='1D Spectrum List',
                            sources='1D Spectrum at index: 5')
    # The length of existing_data_in_dc should now match the new_spectrum_list
    # not the combination of spectrum lists since it resets
    assert len(test_obj.existing_data_in_dc) == len(new_spectrum_list)

    new_dh_list = list(test_obj.existing_data_in_dc.keys())
    test_obj.data_hashes = list(test_obj.existing_data_in_dc.keys())
    # Although two SpectrumList objects are loaded into the data collection,
    # they share no data in common so only one value should be True
    assert sum(test_obj.existing_data_in_dc.values()) == 1
    assert test_obj.existing_data_in_dc[new_dh_list[-1]] is True

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

    deconfigged_helper.app.data_item_remove(test_obj.app.data_collection[1].data.label)
    # Again, existing_data_in_dc is updated from `_update_existing_data_in_dc`
    # in app.py, however we want to doublecheck that
    # reset_and_check_existing_data_in_dc works as expected
    assert len(test_obj.existing_data_in_dc) == len(new_spectrum_list)
    assert sum(test_obj.existing_data_in_dc.values()) == 0

    test_obj.reset_and_check_existing_data_in_dc()
    assert len(test_obj.existing_data_in_dc) == len(new_spectrum_list)
    assert sum(test_obj.existing_data_in_dc.values()) == 0

