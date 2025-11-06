import pytest
from jdaviz.core.user_api import ViewerCreatorUserApi


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


class TestViewerCreatorObject:
    @pytest.fixture(autouse=True)
    def _setup(self, deconfigged_helper, spectrum1d, spectrum1d_nm, spectrum2d):
        self.spectrum1d = spectrum1d
        self.spectrum1d_nm = spectrum1d_nm
        self.spectrum2d = spectrum2d
        deconfigged_helper.load(spectrum1d, format='1D Spectrum')
        self.dcf_helper = deconfigged_helper
        self.creator = deconfigged_helper.new_viewers['1D Spectrum']._obj

    def test_viewer_creator_initialization(self):
        """
        Test that viewer creator initializes with correct defaults.
        """
        assert self.creator.viewer_type == '1D Spectrum'
        assert self.creator.is_relevant is True
        assert self.creator.viewer_label_auto is True
        # Since we autouse the fixture, there is already one loaded dataset
        # so the default now has (1)
        assert self.creator.viewer_label_default == '1D Spectrum (1)'
        assert self.creator.viewer_label_invalid_msg == ''
        assert self.creator.dataset.multiselect is True

        # Check that callbacks exist (they may be None or callable)
        assert hasattr(self.creator, 'set_active_callback')
        assert hasattr(self.creator, 'open_callback')
        assert hasattr(self.creator, 'close_callback')

        # Check that user_api property returns the correct type
        user_api = self.dcf_helper.new_viewers['1D Spectrum']
        assert isinstance(user_api, ViewerCreatorUserApi)

        assert 'is_spectrum' in self.creator.dataset.filters

    def test_viewer_creator_close_in_tray(self):
        """
        Test close_in_tray method with and without closing sidebar.
        """
        # Test without closing sidebar
        self.creator.close_in_tray(close_sidebar=False)
        # Should not raise an error even if callback is None

        # Test with closing sidebar
        self.dcf_helper.app.state.drawer_content = 'test_content'
        self.creator.close_in_tray(close_sidebar=True)
        assert self.dcf_helper.app.state.drawer_content == ''

    def test_viewer_creator_open_in_tray_callbacks(self):
        """
        Test that open_in_tray raises error without set_active_callback
        and succeeds with proper callbacks.
        """
        # Remove the callback to test error handling
        self.creator.set_active_callback = None

        msg = 'set_active_callback must be set to open dialog to specific tab'
        with pytest.raises(NotImplementedError, match=msg):
            self.creator.open_in_tray()

        # Now test with proper callbacks
        callback_called = []

        def mock_set_active(label):
            callback_called.append(('set_active', label))

        def mock_open():
            callback_called.append(('open',))

        self.creator.set_active_callback = mock_set_active
        self.creator.open_callback = mock_open

        self.creator.open_in_tray()

        assert ('set_active', '1D Spectrum') in callback_called
        assert ('open',) in callback_called

    def test_viewer_creator_is_relevant_changes(self):
        """
        Test that is_relevant updates based on available datasets.
        """
        assert self.creator.is_relevant is True

        # Check that it appears in new_viewer_items
        labels = [ti['label'] for ti in self.dcf_helper.app.state.new_viewer_items]
        assert '1D Spectrum' in labels
        idx = labels.index('1D Spectrum')
        assert self.dcf_helper.app.state.new_viewer_items[idx]['is_relevant'] is True

    def test_viewer_label_validation_duplicate(self):
        """
        Test that duplicate viewer labels are properly rejected.
        """
        # Create first viewer
        viewer1 = self.dcf_helper.new_viewers['1D Spectrum']()
        assert viewer1._obj.id == '1D Spectrum (1)'

        # Try to create another with the same label
        creator = self.dcf_helper.new_viewers['1D Spectrum']._obj
        # The default should update to avoid conflict
        assert creator.viewer_label_default != '1D Spectrum'

        creator.viewer_label_value = '1D Spectrum'

        msg = "Viewer label '1D Spectrum' already in use."
        assert creator.viewer_label_invalid_msg == msg

        # Calling should raise ValueError
        with pytest.raises(ValueError, match=msg):
            creator()

    def test_viewer_creator_with_datasets(self):
        """
        Test creating viewer with single/multiple selected datasets.
        """
        # Select dataset
        self.creator.dataset.selected = ['1D Spectrum']

        # Create viewer
        viewer = self.creator()
        # Viewer should have the dataset loaded
        assert len(viewer._obj.data_collection) == 1

        # Load in a second spectrum but first check that the observer works
        assert self.creator.is_relevant is True
        initial_item_count = len(self.creator.dataset.items)
        # Load another one in
        self.dcf_helper.load(self.spectrum1d_nm, format='1D Spectrum')

        # Should still be relevant with more items per the observer
        assert self.creator.is_relevant is True
        assert len(self.creator.dataset.items) > initial_item_count

        # Select multiple datasets
        available_datasets = [item['label'] for item in self.creator.dataset.items]
        self.creator.dataset.selected = available_datasets[:2]
        viewer = self.creator()

        # Viewer should have both datasets
        assert len(viewer._obj.data_collection) == 2

    def test_viewer_creator_observer_without_viewer_attribute(self):
        """
        Test that observers handle missing viewer attribute gracefully.
        """
        # Temporarily remove viewer attribute if it exists
        had_viewer = hasattr(self.creator, 'viewer')
        original_viewer = None
        if had_viewer:
            original_viewer = self.creator.viewer
            delattr(self.creator, 'viewer')

        # These should not raise errors
        self.creator._viewer_label_value_changed()
        self.creator._viewer_items_changed()

        # Restore viewer attribute
        if had_viewer and original_viewer is not None:
            self.creator.viewer = original_viewer

    def test_multiple_viewer_types(self):
        """
        Test that multiple viewer types can coexist.
        """
        self.dcf_helper.load(self.spectrum2d, format='2D Spectrum')

        # Should have multiple viewer types available
        assert '1D Spectrum' in self.dcf_helper.new_viewers
        assert '2D Spectrum' in self.dcf_helper.new_viewers

        # Create viewers of different types
        viewer1d = self.dcf_helper.new_viewers['1D Spectrum']()
        viewer2d = self.dcf_helper.new_viewers['2D Spectrum']()

        assert viewer1d._obj.id != viewer2d._obj.id

    def test_vue_create_clicked(self):
        """
        Test that vue_create_clicked calls the viewer creator.
        """
        initial_viewer_count = len(self.dcf_helper.viewers)

        # Call vue method
        self.creator.vue_create_clicked()

        # Should have created a new viewer
        assert len(self.dcf_helper.viewers) == initial_viewer_count + 1

    def test_viewer_creator_with_custom_label(self):
        """
        Test creating viewer with custom label.
        """
        # Set custom label
        custom_label = 'My Custom Viewer'
        self.creator.viewer_label_value = custom_label
        self.creator.viewer_label_auto = False

        # Should not have validation error
        assert self.creator.viewer_label_invalid_msg == ''

        # Create viewer
        viewer = self.creator()

        # Should have custom label
        assert viewer._obj.id == custom_label
