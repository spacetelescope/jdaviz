from unittest.mock import patch

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
        ldr.format = '1D Spectrum List'
        ldr.importer.sources.selected = '1D Spectrum at index: 0'
        ldr.load()

        # The data hashes update in the SpectrumList importer but are different from the
        # data hashes in our original test_obj
        dh_list = ldr.importer.sources.data_hashes
        labels_list = ldr.importer.sources.labels
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
        ldr.format = '1D Spectrum List'
        ldr.importer.sources.selected = '1D Spectrum at index: 5'
        ldr.load()

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
                      '1D Spectrum List': premade_spectrum_list,
                      '1D Spectrum Concatenated': premade_spectrum_list,
                      'Catalog': sky_coord_only_source_catalog}

        # TODO: Remove when this dev flag is no longer needed
        deconfigged_helper.app.state.catalogs_in_dc = True
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
