"""
Unit tests for data renaming functionality.
"""
import pytest


def test_data_rename_message():
    """
    Test that DataRenamedMessage is properly defined and can be
    instantiated.
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
    
    # Verify data was added
    assert 'label_before' in dcf_dc.labels
    assert 'label_before' in state_items_before

    # Rename the data
    deconfigged_helper.app._rename_data('label_before', 'label_after')

    # Check state.data_items was updated
    state_items_after = [item['name'] for item in deconfigged_helper.app.state.data_items]

    # Verify old name is gone and new name exists
    assert 'label_before' not in dcf_dc.labels
    assert 'label_before' not in state_items_after
    assert 'label_after' in dcf_dc.labels
    assert 'label_after' in state_items_after

    # Verify the data object's label was updated
    data_obj = deconfigged_helper.app.data_collection['label_after']
    assert data_obj.label == 'label_after'


def test_rename_data_invalid_name(deconfigged_helper):
    """
    Test that renaming to a non-existent data raises an error.
    """
    with pytest.raises(ValueError):
        deconfigged_helper.app._rename_data('nonexistent', 'new_name')


def test_rename_data_duplicate_name(deconfigged_helper, image_hdu_wcs):
    """
    Test that renaming to an existing name raises an error.
    """
    deconfigged_helper.load(image_hdu_wcs, format='Image', data_label='data1')
    deconfigged_helper.load(image_hdu_wcs, format='Image', data_label='data2')

    # Try to rename data1 to data2 (which already exists)
    with pytest.raises(ValueError):
        deconfigged_helper.app._rename_data('data1', 'data2')


def test_rename_data_updates_reserved_labels(deconfigged_helper, image_hdu_wcs):
    """
    Test that renaming updates the _reserved_labels set.
    """
    deconfigged_helper.load(image_hdu_wcs, format='Image', data_label='reserved_test')

    # Check old label is in reserved labels
    assert 'reserved_test' in deconfigged_helper.app._reserved_labels

    # Rename
    deconfigged_helper.app._rename_data('reserved_test', 'reserved_test_new')

    # Check labels were updated
    assert 'reserved_test' not in deconfigged_helper.app._reserved_labels
    assert 'reserved_test_new' in deconfigged_helper.app._reserved_labels


def test_rename_data_with_layer_icons(deconfigged_helper, image_hdu_wcs):
    """
    Test that layer icons are updated when renaming data.
    """
    deconfigged_helper.load(image_hdu_wcs, format='Image', data_label='icon_test')

    # Verify icon exists for the data
    assert 'icon_test' in deconfigged_helper.app.state.layer_icons

    # Get the icon
    icon = deconfigged_helper.app.state.layer_icons['icon_test']

    # Rename
    deconfigged_helper.app._rename_data('icon_test', 'icon_test_new')

    # Verify old icon is gone and new icon exists with same value
    assert 'icon_test' not in deconfigged_helper.app.state.layer_icons
    assert 'icon_test_new' in deconfigged_helper.app.state.layer_icons
    assert deconfigged_helper.app.state.layer_icons['icon_test_new'] == icon


def test_rename_data_renaming_flag(deconfigged_helper, image_hdu_wcs):
    """
    Test that _renaming_data flag is properly set and cleared.
    """
    deconfigged_helper.load(image_hdu_wcs, format='Image', data_label='flag_test')

    # Flag should be False initially
    assert deconfigged_helper.app._renaming_data is False

    # We can't easily intercept during the rename, but we can verify
    # it's False afterward
    deconfigged_helper.app._rename_data('flag_test', 'flag_test_new')
    assert deconfigged_helper.app._renaming_data is False


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
    deconfigged_helper.app._rename_data('message_test', 'message_test_new')

    # Check message was broadcast
    assert len(messages_received) > 0
    msg = messages_received[-1]
    assert msg.old_label == 'message_test'
    assert msg.new_label == 'message_test_new'


def test_rename_data_no_auto_extraction_on_2d_spectrum(deconfigged_helper, spectrum2d):
    """
    Test that renaming a 2D spectrum does NOT trigger auto-extraction
    of a 1D spectrum.

    This is the critical test case that verifies the fix for the
    auto-extraction issue.
    """
    # Load the 2D spectrum
    deconfigged_helper.load(spectrum2d, format='2D Spectrum',
                            data_label='2d_spectrum')
    specviz2d_dc = deconfigged_helper.app.data_collection

    # Record the current number of data items
    labels_before = set(specviz2d_dc.labels)

    # Rename the 2D spectrum
    deconfigged_helper.app._rename_data('2d_spectrum', '2d_spectrum_renamed')

    # Verify rename was successful
    assert '2d_spectrum_renamed' in specviz2d_dc.labels
    assert '2d_spectrum' not in specviz2d_dc.labels

    # CRITICAL: Verify NO new data was auto-extracted
    # The number of data items should remain the same (or only increase
    # if there was already a 1D spectrum that got its name updated)
    labels_after = set(specviz2d_dc.labels)

    # The only new labels should be from renaming (if any extraction
    # happened, there would be additional extracted spectrum names)
    assert len(labels_after) == len(labels_before)


def test_rename_data_with_children(deconfigged_helper, spectrum2d):
    """
    Test renaming parent data also renames child data labels.

    This tests the new feature where renaming a parent data entry
    automatically renames all child data entries while preserving
    their suffix. For example:
    - 'spectrum 2d' -> 'my spectrum'
    - 'spectrum 2d (auto-ext)' -> 'my spectrum (auto-ext)'
    """
    # Load parent data
    deconfigged_helper.load(spectrum2d, format='2D Spectrum', data_label='2d_spectrum')

    # Verify initial state
    dcf_dc = deconfigged_helper.app.data_collection
    assert '2d_spectrum' in dcf_dc.labels
    assert '2d_spectrum (auto-ext)' in dcf_dc.labels

    # Rename parent data - should also rename child
    deconfigged_helper.app._rename_data('2d_spectrum', 'new_2d_spectrum', rename_linked_data=True)

    # Verify parent and child were renamed
    assert '2d_spectrum' not in dcf_dc.labels
    assert '2d_spectrum (auto-ext)' not in dcf_dc.labels

    assert 'new_2d_spectrum' in dcf_dc.labels
    assert 'new_2d_spectrum (auto-ext)' in dcf_dc.labels
