

import pytest


def test_viewer_creator_relevance(deconfigged_helper, spectrum1d, spectrum2d):
    assert len(deconfigged_helper.new_viewers) == 0
    deconfigged_helper.load(spectrum1d, format='1D Spectrum')
    # 1D Spectrum, Scatter, Histogram
    assert len(deconfigged_helper.new_viewers) == 3
    deconfigged_helper.load(spectrum2d, format='2D Spectrum')
    # 1D Spectrum, 2D Spectrum, Scatter, Histogram
    assert len(deconfigged_helper.new_viewers) == 4


def test_viewer_creation(deconfigged_helper, spectrum1d):
    deconfigged_helper.load(spectrum1d, format='1D Spectrum')
    assert len(deconfigged_helper.viewers) == 1
    deconfigged_helper.new_viewers['1D Spectrum']()
    assert len(deconfigged_helper.viewers) == 2


def test_viewer_creator_initialization(deconfigged_helper, spectrum1d):
    """
    Test that viewer creator initializes with correct defaults.
    """
    deconfigged_helper.load(spectrum1d, format='1D Spectrum')
    creator = deconfigged_helper.new_viewers['1D Spectrum']._obj

    assert creator.viewer_type == '1D Spectrum'
    assert creator.is_relevant is True
    assert creator.viewer_label_auto is True
    assert creator.viewer_label_default == '1D Spectrum'
    assert creator.viewer_label_invalid_msg == ''
    assert creator.dataset.multiselect is True


def test_viewer_creator_callbacks(deconfigged_helper, spectrum1d):
    """
    Test that callbacks are properly stored during initialization.
    """
    deconfigged_helper.load(spectrum1d, format='1D Spectrum')
    creator = deconfigged_helper.new_viewers['1D Spectrum']._obj

    # Check that callbacks exist (they may be None or callable)
    assert hasattr(creator, 'set_active_callback')
    assert hasattr(creator, 'open_callback')
    assert hasattr(creator, 'close_callback')


def test_viewer_creator_user_api(deconfigged_helper, spectrum1d):
    """
    Test that user_api property returns ViewerCreatorUserApi.
    """
    deconfigged_helper.load(spectrum1d, format='1D Spectrum')
    from jdaviz.core.user_api import ViewerCreatorUserApi
    user_api = deconfigged_helper.new_viewers['1D Spectrum']

    assert isinstance(user_api, ViewerCreatorUserApi)


def test_viewer_creator_close_in_tray(deconfigged_helper, spectrum1d):
    """
    Test close_in_tray method with and without closing sidebar.
    """
    deconfigged_helper.load(spectrum1d, format='1D Spectrum')
    creator = deconfigged_helper.new_viewers['1D Spectrum']._obj

    # Test without closing sidebar
    creator.close_in_tray(close_sidebar=False)
    # Should not raise an error even if callback is None

    # Test with closing sidebar
    deconfigged_helper.app.state.drawer_content = 'test_content'
    creator.close_in_tray(close_sidebar=True)
    assert deconfigged_helper.app.state.drawer_content == ''


def test_viewer_creator_open_in_tray_without_callback(
    deconfigged_helper,
    spectrum1d
):
    """
    Test that open_in_tray raises error without set_active_callback.
    """
    deconfigged_helper.load(spectrum1d, format='1D Spectrum')
    creator = deconfigged_helper.new_viewers['1D Spectrum']._obj

    # Remove the callback to test error handling
    original_callback = creator.set_active_callback
    creator.set_active_callback = None

    msg = 'set_active_callback must be set to open dialog to specific tab'
    with pytest.raises(NotImplementedError, match=msg):
        creator.open_in_tray()

    # Restore callback
    creator.set_active_callback = original_callback


def test_viewer_creator_open_in_tray_with_callback(
    deconfigged_helper,
    spectrum1d
):
    """
    Test that open_in_tray works with proper callbacks.
    """
    deconfigged_helper.load(spectrum1d, format='1D Spectrum')
    creator = deconfigged_helper.new_viewers['1D Spectrum']._obj

    callback_called = []

    def mock_set_active(label):
        callback_called.append(('set_active', label))

    def mock_open():
        callback_called.append(('open',))

    creator.set_active_callback = mock_set_active
    creator.open_callback = mock_open

    creator.open_in_tray()

    assert ('set_active', '1D Spectrum') in callback_called
    assert ('open',) in callback_called


def test_viewer_creator_is_relevant_changes(
    deconfigged_helper,
    spectrum1d
):
    """
    Test that is_relevant updates based on available datasets.
    """
    # Initially no viewers should be relevant
    assert len(deconfigged_helper.new_viewers) == 0

    # Load data and check relevance
    deconfigged_helper.load(spectrum1d, format='1D Spectrum')
    creator = deconfigged_helper.new_viewers['1D Spectrum']._obj

    assert creator.is_relevant is True

    # Check that it appears in new_viewer_items
    labels = [
        ti['label'] for ti in deconfigged_helper.app.state.new_viewer_items
    ]
    assert '1D Spectrum' in labels
    idx = labels.index('1D Spectrum')
    assert (
        deconfigged_helper.app.state.new_viewer_items[idx]['is_relevant']
        is True
    )


def test_viewer_label_validation_duplicate(
    deconfigged_helper,
    spectrum1d
):
    """
    Test that duplicate viewer labels are properly rejected.
    """
    deconfigged_helper.load(spectrum1d, format='1D Spectrum')

    # Create first viewer
    viewer1 = deconfigged_helper.new_viewers['1D Spectrum']()
    assert viewer1.viewer_id == '1D Spectrum'

    # Try to create another with the same label
    creator = deconfigged_helper.new_viewers['1D Spectrum']._obj
    creator.viewer_label_value = '1D Spectrum'

    msg = "Viewer label '1D Spectrum' already in use."
    assert creator.viewer_label_invalid_msg == msg

    # Calling should raise ValueError
    with pytest.raises(ValueError, match=msg):
        creator()


def test_viewer_label_auto_update(deconfigged_helper, spectrum1d):
    """
    Test that viewer label default updates to avoid conflicts.
    """
    deconfigged_helper.load(spectrum1d, format='1D Spectrum')

    # Create first viewer with default label
    viewer1 = deconfigged_helper.new_viewers['1D Spectrum']()
    assert viewer1.viewer_id == '1D Spectrum'

    # Get creator for next viewer
    creator = deconfigged_helper.new_viewers['1D Spectrum']._obj

    # The default should update to avoid conflict
    assert creator.viewer_label_default != '1D Spectrum'


def test_viewer_creator_with_datasets(deconfigged_helper, spectrum1d):
    """
    Test creating viewer with pre-selected datasets.
    """
    deconfigged_helper.load(spectrum1d, format='1D Spectrum')
    creator = deconfigged_helper.new_viewers['1D Spectrum']._obj

    # Select dataset
    creator.dataset.selected = [spectrum1d.meta.get('FILENAME', 'Unknown')]

    # Create viewer
    viewer = creator()

    # Viewer should have the dataset loaded
    assert len(viewer.data()) > 0


def test_viewer_creator_with_multiple_datasets(
    deconfigged_helper,
    spectrum1d,
    spectrum1d_nm
):
    """
    Test creating viewer with multiple selected datasets.
    """
    deconfigged_helper.load(spectrum1d, format='1D Spectrum')
    deconfigged_helper.load(spectrum1d_nm, format='1D Spectrum')

    creator = deconfigged_helper.new_viewers['1D Spectrum']._obj

    # Select multiple datasets
    available_datasets = [item['label'] for item in creator.dataset.items]
    creator.dataset.selected = available_datasets[:2]

    # Create viewer
    viewer = creator()

    # Viewer should have both datasets
    assert len(viewer.data()) >= 2


def test_vue_create_clicked(deconfigged_helper, spectrum1d):
    """
    Test that vue_create_clicked calls the viewer creator.
    """
    deconfigged_helper.load(spectrum1d, format='1D Spectrum')
    creator = deconfigged_helper.new_viewers['1D Spectrum']._obj

    initial_viewer_count = len(deconfigged_helper.viewers)

    # Call vue method
    creator.vue_create_clicked()

    # Should have created a new viewer
    assert len(deconfigged_helper.viewers) == initial_viewer_count + 1


def test_viewer_creator_dataset_filters(deconfigged_helper, spectrum1d):
    """
    Test that dataset filters are properly applied.
    """
    deconfigged_helper.load(spectrum1d, format='1D Spectrum')
    creator = deconfigged_helper.new_viewers['1D Spectrum']._obj

    assert 'is_not_wcs_only' in creator.dataset.filters
    assert 'not_child_layer' in creator.dataset.filters


def test_viewer_creator_returns_user_api(deconfigged_helper, spectrum1d):
    """
    Test that calling creator returns viewer user API.
    """
    deconfigged_helper.load(spectrum1d, format='1D Spectrum')

    viewer = deconfigged_helper.new_viewers['1D Spectrum']()

    # Should return a viewer user API object
    assert hasattr(viewer, 'viewer_id')
    assert hasattr(viewer, 'data')


def test_viewer_creator_with_custom_label(deconfigged_helper, spectrum1d):
    """
    Test creating viewer with custom label.
    """
    deconfigged_helper.load(spectrum1d, format='1D Spectrum')
    creator = deconfigged_helper.new_viewers['1D Spectrum']._obj

    # Set custom label
    custom_label = 'My Custom Viewer'
    creator.viewer_label_value = custom_label
    creator.viewer_label_auto = False

    # Should not have validation error
    assert creator.viewer_label_invalid_msg == ''

    # Create viewer
    viewer = creator()

    # Should have custom label
    assert viewer.viewer_id == custom_label


def test_multiple_viewer_types(
    deconfigged_helper,
    spectrum1d,
    spectrum2d
):
    """
    Test that multiple viewer types can coexist.
    """
    deconfigged_helper.load(spectrum1d, format='1D Spectrum')
    deconfigged_helper.load(spectrum2d, format='2D Spectrum')

    # Should have multiple viewer types available
    assert '1D Spectrum' in deconfigged_helper.new_viewers
    assert '2D Spectrum' in deconfigged_helper.new_viewers

    # Create viewers of different types
    viewer1d = deconfigged_helper.new_viewers['1D Spectrum']()
    viewer2d = deconfigged_helper.new_viewers['2D Spectrum']()

    assert viewer1d.viewer_id != viewer2d.viewer_id


def test_viewer_creator_observer_without_viewer_attribute(
    deconfigged_helper,
    spectrum1d
):
    """
    Test that observers handle missing viewer attribute gracefully.
    """
    deconfigged_helper.load(spectrum1d, format='1D Spectrum')
    creator = deconfigged_helper.new_viewers['1D Spectrum']._obj

    # Temporarily remove viewer attribute if it exists
    had_viewer = hasattr(creator, 'viewer')
    original_viewer = None
    if had_viewer:
        original_viewer = creator.viewer
        delattr(creator, 'viewer')

    # These should not raise errors
    creator._viewer_label_value_changed()
    creator._viewer_items_changed()

    # Restore viewer attribute
    if had_viewer and original_viewer is not None:
        creator.viewer = original_viewer


def test_viewer_creator_dataset_items_observer(
    deconfigged_helper,
    spectrum1d,
    spectrum1d_nm
):
    """
    Test that dataset_items observer updates relevance.
    """
    # Start with no data
    assert len(deconfigged_helper.new_viewers) == 0

    # Load first spectrum
    deconfigged_helper.load(spectrum1d, format='1D Spectrum')
    creator = deconfigged_helper.new_viewers['1D Spectrum']._obj

    assert creator.is_relevant is True
    initial_item_count = len(creator.dataset.items)

    # Load second spectrum
    deconfigged_helper.load(spectrum1d_nm, format='1D Spectrum')

    # Should still be relevant with more items
    assert creator.is_relevant is True
    assert len(creator.dataset.items) > initial_item_count
