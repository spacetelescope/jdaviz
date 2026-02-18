"""
Unit tests for data renaming functionality.
"""
import pytest


def test_data_rename_message():
    """
    Test that DataRenamedMessage is properly defined and can be instantiated.
    """
    from jdaviz.core.events import DataRenamedMessage

    # Create a mock data object
    class MockData:
        def __init__(self, label):
            self.label = label

    data = MockData('old_label')
    msg = DataRenamedMessage(data, 'old_label', 'new_label', sender=None)

    assert msg.data == data
    assert msg.old_label == 'old_label'
    assert msg.new_label == 'new_label'


@pytest.mark.parametrize('input_data, data_format', [
    ['image_hdu_wcs', 'Image'],
    ['spectrum1d', '1D Spectrum'],
    ['spectrum2d', '2D Spectrum'],
    ['spectrum1d_cube', '3D Spectrum']
])
def test_basic_data_rename(deconfigged_helper, input_data, data_format, request):
    """
    Test basic data rename functionality.
    """
    # Load a simple image
    deconfigged_helper.load(request.getfixturevalue(input_data),
                            format=data_format,
                            data_label='label_before')
    # Check data collection
    dcf_dc = deconfigged_helper.app.data_collection
    # Check state.data_items
    state_items_before = [item['name'] for item in deconfigged_helper.app.state.data_items]
    # Check the layer_icon
    icon = deconfigged_helper.app.state.layer_icons['label_before']

    # Verify data was added in the data collection, state.data_items, and layer_icons
    assert 'label_before' in dcf_dc.labels
    assert 'label_before' in state_items_before
    assert 'label_before' in deconfigged_helper.app.state.layer_icons
    # Check _renaming_data flag
    assert deconfigged_helper.app._renaming_data is False

    # Rename the data
    deconfigged_helper.app.rename_data('label_before', 'label_after')

    # Check state.data_items was updated
    state_items_after = [item['name'] for item in deconfigged_helper.app.state.data_items]

    # Verify old name is gone and new name exists
    assert 'label_before' not in dcf_dc.labels
    assert 'label_before' not in state_items_after

    assert 'label_after' in dcf_dc.labels
    assert 'label_after' in state_items_after

    assert 'label_before' not in deconfigged_helper.app.state.layer_icons
    assert 'label_after' in deconfigged_helper.app.state.layer_icons

    # Check _renaming_data flag again (can't interrupt during rename, but can check after)
    assert deconfigged_helper.app._renaming_data is False

    # Verify the data object's label was updated
    data_obj = deconfigged_helper.app.data_collection['label_after']
    assert data_obj.label == 'label_after'

    # Verify that the icon reference has changed but not the icon
    assert deconfigged_helper.app.state.layer_icons['label_after'] == icon


def test_rename_data_errors(deconfigged_helper, image_hdu_wcs):
    """
    Test that:
     * renaming to a non-existent data raises an error.
     * renaming to an existing name raises an error.
     * renaming to a reserved label raises an error.
    """
    deconfigged_helper.load(image_hdu_wcs, format='Image', data_label='data1')

    # Try to rename non-existent data
    with pytest.raises(ValueError):
        deconfigged_helper.app.rename_data('nonexistent', 'new_name')

    deconfigged_helper.load(image_hdu_wcs, format='Image', data_label='data2')

    # Try to rename data1 to data2 (which already exists)
    with pytest.raises(ValueError):
        deconfigged_helper.app.rename_data('data1', 'data2')

    # Try to rename with a reserved label
    reserved_label = list(deconfigged_helper.app._reserved_labels)[0]
    with pytest.raises(ValueError):
        deconfigged_helper.app.rename_data('data1', reserved_label)


def test_rename_data_updates_reserved_labels(deconfigged_helper, image_hdu_wcs):
    """
    Test that renaming updates the _reserved_labels set.
    """
    deconfigged_helper.load(image_hdu_wcs, format='Image', data_label='reserved_test')

    # Check old label is in reserved labels
    assert 'reserved_test' in deconfigged_helper.app._reserved_labels

    # Rename
    deconfigged_helper.app.rename_data('reserved_test', 'reserved_test_new')

    # Check labels were updated
    assert 'reserved_test' not in deconfigged_helper.app._reserved_labels
    assert 'reserved_test_new' in deconfigged_helper.app._reserved_labels


def test_rename_data_broadcasts_message(deconfigged_helper, image_hdu_wcs):
    """
    Test that renaming data broadcasts DataRenamedMessage.
    """
    from jdaviz.core.events import DataRenamedMessage
    from glue.core.hub import HubListener

    deconfigged_helper.load(image_hdu_wcs, format='Image', data_label='message_test')

    # Track messages received
    messages_received = []

    # Create a proper HubListener to capture messages
    class MessageCapture(HubListener):
        def __init__(self):
            super().__init__()

        def handle_data_renamed(self, msg):
            if isinstance(msg, DataRenamedMessage):
                messages_received.append(msg)

    listener = MessageCapture()

    # Subscribe to messages
    deconfigged_helper.app.hub.subscribe(listener, DataRenamedMessage,
                                         handler=listener.handle_data_renamed)

    # Rename
    deconfigged_helper.app.rename_data('message_test', 'message_test_new')

    # Check message was broadcast
    msg = messages_received[-1]
    assert msg.old_label == 'message_test'
    assert msg.new_label == 'message_test_new'


def test_rename_data_no_auto_extraction_on_2d_spectrum(deconfigged_helper, spectrum2d):
    """
    Test that renaming a 2D spectrum does NOT trigger auto-extraction of a 1D spectrum.
    """
    # Load the 2D spectrum
    deconfigged_helper.load(spectrum2d, format='2D Spectrum', data_label='2d_spectrum')
    dcf_dc = deconfigged_helper.app.data_collection

    assert '2d_spectrum' in dcf_dc.labels
    assert '2d_spectrum (auto-ext)' in dcf_dc.labels

    # Record the current number of data items
    labels_before = set(dcf_dc.labels)

    # Rename the 2D spectrum
    deconfigged_helper.app.rename_data('2d_spectrum', '2d_spectrum_renamed')

    # Verify rename (of 2d spectrum only) was successful
    assert '2d_spectrum' not in dcf_dc.labels
    assert '2d_spectrum_renamed' in dcf_dc.labels
    assert '2d_spectrum_renamed (auto-ext)' in dcf_dc.labels

    # Verify no new data was auto-extracted
    # The number of data items should remain the same (or only increase
    # if there was already a 1D spectrum that got its name updated)
    labels_after = set(dcf_dc.labels)

    # The only new labels should be from renaming (if any extraction
    # happened, there would be additional extracted spectrum names)
    assert len(labels_after) == len(labels_before)


def test_rename_data_preserves_dataset_selected(deconfigged_helper, spectrum1d):
    """
    Test that renaming data preserves dataset_selected in plugins like Model Fitting.

    This test verifies that when rename_data is called, the dataset_selected
    trait in plugins is updated to the new name and not reset to a default value.
    """
    # Load two spectra so we have multiple options
    deconfigged_helper.load(spectrum1d, data_label='spectrum_a')
    deconfigged_helper.load(spectrum1d, data_label='spectrum_b')

    dcf_app = deconfigged_helper.app

    # Test a few plugins that use dataset_selected for posterity
    for plugin in ['Model Fitting', 'Line Analysis', 'Gaussian Smooth']:
        model_fitting = deconfigged_helper.plugins[plugin]._obj
        model_fitting.dataset_selected = 'spectrum_b'
        dcf_app.rename_data('spectrum_b', 'spectrum_c')

        # Verify the selection was updated to the new name, not reset to default
        assert model_fitting.dataset_selected == 'spectrum_c'

        # Also verify the data collection was updated
        assert 'spectrum_b' not in dcf_app.data_collection.labels
        assert 'spectrum_c' in dcf_app.data_collection.labels

        # Reset
        dcf_app.rename_data('spectrum_c', 'spectrum_b')
