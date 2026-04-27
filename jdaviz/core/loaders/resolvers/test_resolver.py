from jdaviz.app import PrivateApplication
from jdaviz.core.loaders.resolvers.resolver import BaseResolver, find_closest_polygon_mark
from jdaviz.core.marks import RegionOverlay
from jdaviz.utils import find_polygon_mark_with_skewer
from jdaviz.core.events import FootprintOverlayClickMessage

import numpy as np
import pytest
from astropy.table import Table


# Create a minimal test class that mimics the resolver behavior
# without this we get an error when attempting to use BaseResolver directly
class ABC(BaseResolver):
    template = ''

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


def test_server_is_remote_callback():
    # Create app instance
    app = PrivateApplication()

    # Test the sync
    test_obj = ABC(app=app)
    settings = app.state.settings

    # Check default
    assert settings.get('server_is_remote') is False
    assert settings.get('server_is_remote') == test_obj.server_is_remote

    settings['server_is_remote'] = True
    assert settings.get('server_is_remote') == test_obj.server_is_remote

    # Ensure setting test_obj.server_is_remote does not backpropagate
    # (this behavior could change)
    test_obj.server_is_remote = False
    assert settings.get('server_is_remote') != test_obj.server_is_remote


def test_footprint_workflow(deconfigged_helper, image_nddata_wcs):
    deconfigged_helper.load(image_nddata_wcs, format='Image', data_label='test_image')

    table = Table()
    table['Dataset'] = ['obs1', 'obs2', 'obs3']
    table['s_region'] = [
        'POLYGON 337.51 -20.84 337.52 -20.84 337.52 -20.83 337.51 -20.83',
        'POLYGON 337.52 -20.84 337.53 -20.84 337.53 -20.83 337.52 -20.83',
        'POLYGON 337.53 -20.84 337.54 -20.84 337.54 -20.83 337.53 -20.83',
    ]

    ldr = deconfigged_helper.loaders['object']
    ldr.object = table
    ldr.treat_table_as_query = True

    assert ldr._obj.parsed_input_is_query is True
    assert ldr._obj.observation_table_populated is True
    assert 's_region' in ldr._obj.observation_table.headers_avail

    ldr._obj.vue_link_by_wcs()
    assert ldr._obj.is_wcs_linked is True

    ldr._obj.toggle_custom_toolbar()
    assert ldr._obj.custom_toolbar_enabled is True

    # Check footprints in viewer
    viewer = list(deconfigged_helper._app.get_viewers_of_cls('ImvizImageView'))[0]
    footprints = [m for m in viewer.figure.marks if isinstance(m, RegionOverlay)]
    assert len(footprints) == 3
    assert sorted([m.label for m in footprints]) == [0, 1, 2]

    mark = footprints[1]
    px, py = np.mean(mark.x), np.mean(mark.y)
    idx = find_closest_polygon_mark(px, py, footprints)
    assert idx is not None
    assert 0 <= idx < 3

    ldr._obj.toggle_custom_toolbar()
    assert ldr._obj.custom_toolbar_enabled is False
    footprints = [m for m in viewer.figure.marks if isinstance(m, RegionOverlay)]
    assert len(footprints) == 0


def test_remove_footprints(deconfigged_helper, image_nddata_wcs):
    deconfigged_helper.load(image_nddata_wcs, format='Image', data_label='test_image')

    table = Table()
    table['Dataset'] = ['obs1']
    table['s_region'] = [
        'POLYGON 337.499 -20.831 337.501 -20.831 337.501 -20.829 337.499 -20.829'
    ]

    ldr = deconfigged_helper.loaders['object']
    ldr.object = table
    ldr.treat_table_as_query = True
    ldr._obj.vue_link_by_wcs()

    # Display footprints
    ldr._obj.toggle_custom_toolbar()
    viewer = list(deconfigged_helper._app.get_viewers_of_cls('ImvizImageView'))[0]
    footprints = [m for m in viewer.figure.marks if isinstance(m, RegionOverlay)]
    assert len(footprints) == 1

    # Remove footprints
    ldr._obj.toggle_custom_toolbar()

    # Assert marks are removed
    footprints = [m for m in viewer.figure.marks if isinstance(m, RegionOverlay)]
    assert len(footprints) == 0


def test_multiselect(deconfigged_helper, image_nddata_wcs):
    deconfigged_helper.load(image_nddata_wcs, format='Image', data_label='test_image')

    table = Table()
    table['Dataset'] = ['obs1', 'obs2', 'obs3']
    table['s_region'] = [
        'POLYGON 337.499 -20.831 337.501 -20.831 337.501 -20.829 337.499 -20.829',
        'POLYGON 337.502 -20.831 337.504 -20.831 337.504 -20.829 337.502 -20.829',
        'POLYGON 337.505 -20.831 337.507 -20.831 337.507 -20.829 337.505 -20.829'
    ]

    ldr = deconfigged_helper.loaders['object']
    ldr.object = table
    ldr.treat_table_as_query = True
    ldr._obj.vue_link_by_wcs()
    ldr._obj.toggle_custom_toolbar()

    viewer = list(deconfigged_helper._app.get_viewers_of_cls('ImvizImageView'))[0]
    footprints = [m for m in viewer.figure.marks if isinstance(m, RegionOverlay)]
    assert len(footprints) == 3

    # Select observations 0 and 2 via the table
    ldr._obj.observation_table.select_rows([0, 2])

    # Check that selected marks match table selection
    selected_labels = sorted([m.label for m in footprints if m.selected])
    assert selected_labels == [0, 2]


def test_display_valid_footprints(deconfigged_helper, image_nddata_wcs):
    deconfigged_helper.load(image_nddata_wcs, format='Image', data_label='test_image')

    table = Table()
    table['Dataset'] = ['obs1', 'obs2']
    table['s_region'] = [
        'POLYGON 337.499 -20.831 337.501 -20.831 337.501 -20.829 337.499 -20.829',
        'POLYGON 337.502 -20.831 337.504 -20.831 337.504 -20.829 337.502 -20.829'
    ]
    ldr = deconfigged_helper.loaders['object']
    ldr.object = table
    ldr.treat_table_as_query = True
    ldr._obj.vue_link_by_wcs()
    ldr._obj.toggle_custom_toolbar()

    # Assert marks were added
    viewer = list(deconfigged_helper._app.get_viewers_of_cls('ImvizImageView'))[0]
    footprints = [m for m in viewer.figure.marks if isinstance(m, RegionOverlay)]
    assert len(footprints) == 2

    # Verify marks have labels/indices
    for mark in footprints:
        assert isinstance(mark, RegionOverlay)
        assert mark.label in [0, 1]


def test_no_image_data_disables_toolbar(deconfigged_helper):
    table = Table()
    table['Dataset'] = ['obs1']
    table['s_region'] = [
        'POLYGON 337.499 -20.831 337.501 -20.831 337.501 -20.829 337.499 -20.829'
    ]

    ldr = deconfigged_helper.loaders['object']
    ldr.object = table
    ldr.treat_table_as_query = True

    # Although we have footprint data, toolbar should not be enabled
    # because there's no image data to link
    assert len(deconfigged_helper._app.data_collection) == 0
    assert ldr._obj.observation_table_populated is True
    assert ldr._obj.image_data_loaded is False


def test_footprint_with_image_deconfigged(deconfigged_helper, image_nddata_wcs):
    deconfigged_helper.load(image_nddata_wcs, format='Image', data_label='Test Image')
    assert len(deconfigged_helper._app.data_collection) == 1

    table = Table()
    table['Dataset'] = ['obs1']
    table['s_region'] = [
        'POLYGON 337.499 -20.831 337.501 -20.831 337.501 -20.829 337.499 -20.829'
    ]

    ldr = deconfigged_helper.loaders['object']
    ldr.object = table
    ldr.treat_table_as_query = True

    assert ldr._obj.parsed_input_is_query is True
    assert ldr._obj.observation_table_populated is True
    assert ldr._obj.image_data_loaded is True

    ldr._obj.vue_link_by_wcs()
    assert ldr._obj.is_wcs_linked is True

    ldr._obj.toggle_custom_toolbar()
    assert ldr._obj.custom_toolbar_enabled is True
    viewer = list(deconfigged_helper._app.get_viewers_of_cls('ImvizImageView'))[0]
    footprints = [m for m in viewer.figure.marks if isinstance(m, RegionOverlay)]
    assert len(footprints) == 1
    assert footprints[0].label == 0


def test_multiviewer_footprints(deconfigged_helper, image_nddata_wcs):
    deconfigged_helper.load(image_nddata_wcs, format='Image', data_label='Image 1')
    viewer = list(deconfigged_helper._app.get_viewers_of_cls('ImvizImageView'))[0]

    table = Table()
    table['Dataset'] = ['obs1', 'obs2']
    table['s_region'] = [
        'POLYGON 337.499 -20.831 337.501 -20.831 337.501 -20.829 337.499 -20.829',
        'POLYGON 337.502 -20.831 337.504 -20.831 337.504 -20.829 337.502 -20.829'
    ]

    ldr = deconfigged_helper.loaders['object']
    ldr.object = table
    ldr.treat_table_as_query = True
    ldr._obj.vue_link_by_wcs()
    ldr._obj.toggle_custom_toolbar()

    viewer_footprints = [m for m in viewer.figure.marks if isinstance(m, RegionOverlay)]
    assert len(viewer_footprints) == 2
    # Assert labels match
    viewer_labels = sorted([m.label for m in viewer_footprints])
    assert viewer_labels == [0, 1]


def test_multiviewer_selection_sync(deconfigged_helper, image_nddata_wcs):
    deconfigged_helper.load(image_nddata_wcs, format='Image', data_label='Image 1')
    viewer = list(deconfigged_helper._app.get_viewers_of_cls('ImvizImageView'))[0]

    table = Table()
    table['Dataset'] = ['obs1', 'obs2', 'obs3']
    table['s_region'] = [
        'POLYGON 337.499 -20.831 337.501 -20.831 337.501 -20.829 337.499 -20.829',
        'POLYGON 337.502 -20.831 337.504 -20.831 337.504 -20.829 337.502 -20.829',
        'POLYGON 337.505 -20.831 337.507 -20.831 337.507 -20.829 337.505 -20.829'
    ]

    ldr = deconfigged_helper.loaders['object']
    ldr.object = table
    ldr.treat_table_as_query = True
    ldr._obj.vue_link_by_wcs()
    ldr._obj.toggle_custom_toolbar()

    # Select observation in table
    ldr._obj.observation_table.select_rows([0, 2])

    # Check selection is synced in viewer
    footprints = [m for m in viewer.figure.marks if isinstance(m, RegionOverlay)]
    selected_labels = [m.label for m in footprints if m.selected]
    assert sorted(selected_labels) == [0, 2]


def test_add_footprints_to_viewer_method(deconfigged_helper, image_nddata_wcs):
    deconfigged_helper.load(image_nddata_wcs, format='Image', data_label='Image 1')

    table = Table()
    table['Dataset'] = ['obs1']
    table['s_region'] = [
        'POLYGON 337.499 -20.831 337.501 -20.831 337.501 -20.829 337.499 -20.829'
    ]

    ldr = deconfigged_helper.loaders['object']
    ldr.object = table
    ldr.treat_table_as_query = True
    ldr._obj.vue_link_by_wcs()

    # Manually call _add_footprints_to_viewer
    viewer = list(deconfigged_helper._app.get_viewers_of_cls('ImvizImageView'))[0]
    ldr._obj.custom_toolbar_enabled = True
    ldr._obj._add_footprints_to_viewer(viewer)

    # Assert footprints were added
    viewer_footprints = [m for m in viewer.figure.marks if isinstance(m, RegionOverlay)]
    assert len(viewer_footprints) == 1
    assert viewer_footprints[0].label == 0


def test_remove_footprints_from_viewer(deconfigged_helper, image_nddata_wcs):
    deconfigged_helper.load(image_nddata_wcs, format='Image', data_label='Image 1')
    viewer = list(deconfigged_helper._app.get_viewers_of_cls('ImvizImageView'))[0]

    table = Table()
    table['Dataset'] = ['obs1']
    table['s_region'] = [
        'POLYGON 337.499 -20.831 337.501 -20.831 337.501 -20.829 337.499 -20.829'
    ]

    ldr = deconfigged_helper.loaders['object']
    ldr.object = table
    ldr.treat_table_as_query = True
    ldr._obj.vue_link_by_wcs()
    ldr._obj.toggle_custom_toolbar()

    # Assert viewer has footprints
    assert any(isinstance(m, RegionOverlay) for m in viewer.figure.marks)
    # Disable toolbar
    ldr._obj.toggle_custom_toolbar()
    # Assert footprints removed
    assert not any(isinstance(m, RegionOverlay) for m in viewer.figure.marks)


def test_skewer_selection_inside_footprint(deconfigged_helper, image_nddata_wcs):
    """Test that skewer selection only selects when click is inside a footprint."""
    deconfigged_helper.load(image_nddata_wcs, format='Image', data_label='test_image')

    table = Table()
    table['Dataset'] = ['obs1']
    table['s_region'] = [
        'POLYGON 337.499 -20.831 337.501 -20.831 337.501 -20.829 337.499 -20.829'
    ]

    ldr = deconfigged_helper.loaders['object']
    ldr.object = table
    ldr.treat_table_as_query = True
    ldr._obj.vue_link_by_wcs()
    ldr._obj.toggle_custom_toolbar()

    viewer = list(deconfigged_helper._app.get_viewers_of_cls('ImvizImageView'))[0]
    footprints = [m for m in viewer.figure.marks if isinstance(m, RegionOverlay)]
    assert len(footprints) == 1

    # Get center of footprint (should be inside)
    mark = footprints[0]
    center_x = np.mean(mark.x)
    center_y = np.mean(mark.y)

    # Test skewer selection finds the footprint when clicking inside
    indices = find_polygon_mark_with_skewer(center_x, center_y, viewer, footprints)
    assert indices == [0]

    # Test clicking outside footprint (using a point far away)
    far_x = mark.x[0] - 1000
    far_y = mark.y[0] - 1000
    idx_outside = find_polygon_mark_with_skewer(far_x, far_y, viewer, footprints)
    assert idx_outside is None


def test_skewer_selection_smallest_footprint(deconfigged_helper, image_nddata_wcs):
    """Test that skewer selection selects all footprints when multiple contain the click."""
    deconfigged_helper.load(image_nddata_wcs, format='Image', data_label='test_image')

    table = Table()
    table['Dataset'] = ['large', 'small']
    # Create two overlapping footprints - small one inside large one
    table['s_region'] = [
        # Large footprint
        'POLYGON 337.498 -20.832 337.502 -20.832 337.502 -20.828 337.498 -20.828',
        # Small footprint (inside large one)
        'POLYGON 337.499 -20.831 337.501 -20.831 337.501 -20.829 337.499 -20.829'
    ]

    ldr = deconfigged_helper.loaders['object']
    ldr.object = table
    ldr.treat_table_as_query = True
    ldr._obj.vue_link_by_wcs()
    ldr._obj.toggle_custom_toolbar()

    viewer = list(deconfigged_helper._app.get_viewers_of_cls('ImvizImageView'))[0]
    footprints = [m for m in viewer.figure.marks if isinstance(m, RegionOverlay)]
    assert len(footprints) == 2

    # Find the small footprint's center
    small_mark = [m for m in footprints if m.label == 1][0]
    center_x = np.mean(small_mark.x)
    center_y = np.mean(small_mark.y)

    # Click in the center of small footprint (which is also inside large)
    # Should select both footprints (labels 0 and 1)
    indices = find_polygon_mark_with_skewer(center_x, center_y, viewer, footprints)
    assert set(indices) == {0, 1}


def test_skewer_selection_vs_nearest_edge(deconfigged_helper, image_nddata_wcs):
    """Test that skewer selection differs from nearest-edge selection for edge clicks."""
    deconfigged_helper.load(image_nddata_wcs, format='Image', data_label='test_image')

    table = Table()
    table['Dataset'] = ['obs1', 'obs2']
    table['s_region'] = [
        'POLYGON 337.499 -20.831 337.501 -20.831 337.501 -20.829 337.499 -20.829',
        'POLYGON 337.502 -20.831 337.504 -20.831 337.504 -20.829 337.502 -20.829'
    ]

    ldr = deconfigged_helper.loaders['object']
    ldr.object = table
    ldr.treat_table_as_query = True
    ldr._obj.vue_link_by_wcs()
    ldr._obj.toggle_custom_toolbar()

    viewer = list(deconfigged_helper._app.get_viewers_of_cls('ImvizImageView'))[0]
    footprints = [m for m in viewer.figure.marks if isinstance(m, RegionOverlay)]
    assert len(footprints) == 2

    # Click between the two footprints (outside both)
    mark1 = [m for m in footprints if m.label == 0][0]
    mark2 = [m for m in footprints if m.label == 1][0]

    # Point between the two footprints
    between_x = (np.max(mark1.x) + np.min(mark2.x)) / 2
    between_y = (np.max(mark1.y) + np.min(mark2.y)) / 2

    # Nearest-edge selection should find something (closest edge)
    nearest_idx = find_closest_polygon_mark(between_x, between_y, footprints)
    assert nearest_idx is not None

    # Skewer selection should return None (not inside any footprint)
    skewer_idx = find_polygon_mark_with_skewer(between_x, between_y, viewer, footprints)
    assert skewer_idx is None


def test_skewer_selection_with_empty_region(deconfigged_helper, image_nddata_wcs):
    """Test skewer selection handles empty s_region gracefully."""
    deconfigged_helper.load(image_nddata_wcs, format='Image', data_label='test_image')

    table = Table()
    table['Dataset'] = ['obs1', 'obs2']
    table['s_region'] = [
        'POLYGON 337.499 -20.831 337.501 -20.831 337.501 -20.829 337.499 -20.829',
        ''  # Empty region
    ]

    ldr = deconfigged_helper.loaders['object']
    ldr.object = table
    ldr.treat_table_as_query = True
    ldr._obj.vue_link_by_wcs()
    ldr._obj.toggle_custom_toolbar()

    viewer = list(deconfigged_helper._app.get_viewers_of_cls('ImvizImageView'))[0]
    footprints = [m for m in viewer.figure.marks if isinstance(m, RegionOverlay)]
    # Only one footprint should be created (second one is empty)
    assert len(footprints) == 1

    mark = footprints[0]
    center_x = np.mean(mark.x)
    center_y = np.mean(mark.y)

    # Should still work with the single valid footprint
    indices = find_polygon_mark_with_skewer(center_x, center_y, viewer, footprints)
    assert indices == [0]


def test_enable_footprint_selection_tools_api(deconfigged_helper, image_nddata_wcs):
    """Test the enable_footprint_selection_tools API method."""
    deconfigged_helper.load(image_nddata_wcs, format='Image', data_label='test_image')

    table = Table()
    table['Dataset'] = ['obs1']
    table['s_region'] = [
        'POLYGON 337.499 -20.831 337.501 -20.831 337.501 -20.829 337.499 -20.829'
    ]

    ldr = deconfigged_helper.loaders['object']
    ldr.object = table
    ldr.treat_table_as_query = True

    # Should fail without WCS linking
    with pytest.raises(ValueError, match="Images must be linked by WCS"):
        ldr.enable_footprint_selection_tools()

    # Link by WCS
    ldr._obj.vue_link_by_wcs()

    assert not ldr._obj.custom_toolbar_enabled
    ldr.enable_footprint_selection_tools()
    assert ldr._obj.custom_toolbar_enabled

    # Verify footprints are displayed
    viewer = list(deconfigged_helper._app.get_viewers_of_cls('ImvizImageView'))[0]
    footprints = [m for m in viewer.figure.marks if isinstance(m, RegionOverlay)]
    assert len(footprints) == 1


def test_disable_footprint_selection_tools_api(deconfigged_helper, image_nddata_wcs):
    """Test the disable_footprint_selection_tools API method."""
    deconfigged_helper.load(image_nddata_wcs, format='Image', data_label='test_image')

    table = Table()
    table['Dataset'] = ['obs1']
    table['s_region'] = [
        'POLYGON 337.499 -20.831 337.501 -20.831 337.501 -20.829 337.499 -20.829'
    ]

    ldr = deconfigged_helper.loaders['object']
    ldr.object = table
    ldr.treat_table_as_query = True
    ldr._obj.vue_link_by_wcs()

    # Enable first
    ldr.enable_footprint_selection_tools()
    assert ldr._obj.custom_toolbar_enabled

    viewer = list(deconfigged_helper._app.get_viewers_of_cls('ImvizImageView'))[0]
    footprints = [m for m in viewer.figure.marks if isinstance(m, RegionOverlay)]
    assert len(footprints) == 1

    # Now disable
    ldr.disable_footprint_selection_tools()
    assert not ldr._obj.custom_toolbar_enabled

    # Verify footprints are removed
    footprints = [m for m in viewer.figure.marks if isinstance(m, RegionOverlay)]
    assert len(footprints) == 0


def test_enable_without_observation_table(deconfigged_helper, image_nddata_wcs):
    deconfigged_helper.load(image_nddata_wcs, format='Image', data_label='test_image')

    ldr = deconfigged_helper.loaders['object']

    # Try to enable without loading any observation table
    with pytest.raises(ValueError, match="observation table with s_region data"):
        ldr.enable_footprint_selection_tools()


def test_footprint_selection_ctrl_modifier(deconfigged_helper, image_nddata_wcs):
    """Test Ctrl/Cmd+click multi-selection behavior."""
    deconfigged_helper.load(image_nddata_wcs, format='Image', data_label='test_image')

    table = Table()
    table['Dataset'] = ['obs1', 'obs2', 'obs3']
    table['s_region'] = [
        'POLYGON 337.499 -20.831 337.501 -20.831 337.501 -20.829 337.499 -20.829',
        'POLYGON 337.502 -20.831 337.504 -20.831 337.504 -20.829 337.502 -20.829',
        'POLYGON 337.505 -20.831 337.507 -20.831 337.507 -20.829 337.505 -20.829'
    ]

    ldr = deconfigged_helper.loaders['object']
    ldr.object = table
    ldr.treat_table_as_query = True
    ldr._obj.vue_link_by_wcs()
    ldr._obj.toggle_custom_toolbar()

    viewer = list(deconfigged_helper._app.get_viewers_of_cls('ImvizImageView'))[0]
    footprints = [m for m in viewer.figure.marks if isinstance(m, RegionOverlay)]
    assert len(footprints) == 3

    class MockTool:
        def __init__(self, viewer):
            self.viewer = viewer

    mock_tool = MockTool(viewer)

    # Get marks by label
    marks_by_label = {m.label: m for m in footprints}

    # Regular click - selects first footprint
    # Use the centroid of the polygon for a reliable click point
    m0_x, m0_y = np.mean(marks_by_label[0].x), np.mean(marks_by_label[0].y)
    msg = FootprintOverlayClickMessage(
        {'domain': {'x': m0_x, 'y': m0_y}},
        mode='nearest',
        sender=mock_tool
    )
    ldr._obj._on_region_select(msg)
    assert len(ldr._obj.observation_table.selected_rows) == 1
    assert ldr._obj.observation_table.selected_rows[0]['Dataset'] == 'obs1'

    # Ctrl+click on second - adds to selection
    m1_x, m1_y = np.mean(marks_by_label[1].x), np.mean(marks_by_label[1].y)
    msg_ctrl = FootprintOverlayClickMessage(
        {'domain': {'x': m1_x, 'y': m1_y}, 'ctrlKey': True},
        mode='nearest',
        sender=mock_tool
    )
    ldr._obj._on_region_select(msg_ctrl)
    assert len(ldr._obj.observation_table.selected_rows) == 2
    selected_datasets = {row['Dataset'] for row in ldr._obj.observation_table.selected_rows}
    assert selected_datasets == {'obs1', 'obs2'}

    # Ctrl+click on first again - removes from selection
    msg_ctrl_deselect = FootprintOverlayClickMessage(
        {'domain': {'x': m0_x, 'y': m0_y}, 'ctrlKey': True},
        mode='nearest',
        sender=mock_tool
    )
    ldr._obj._on_region_select(msg_ctrl_deselect)
    assert len(ldr._obj.observation_table.selected_rows) == 1
    assert ldr._obj.observation_table.selected_rows[0]['Dataset'] == 'obs2'


def test_footprint_selection_skewer_ctrl_modifier(deconfigged_helper, image_nddata_wcs):
    """Test skewer mode with Ctrl/Cmd+click multi-selection behavior."""
    deconfigged_helper.load(image_nddata_wcs, format='Image', data_label='test_image')

    table = Table()
    table['Dataset'] = ['obs1', 'obs2', 'obs3']
    table['s_region'] = [
        'POLYGON 337.499 -20.831 337.501 -20.831 337.501 -20.829 337.499 -20.829',
        'POLYGON 337.502 -20.831 337.504 -20.831 337.504 -20.829 337.502 -20.829',
        'POLYGON 337.505 -20.831 337.507 -20.831 337.507 -20.829 337.505 -20.829'
    ]

    ldr = deconfigged_helper.loaders['object']
    ldr.object = table
    ldr.treat_table_as_query = True
    ldr._obj.vue_link_by_wcs()
    ldr._obj.toggle_custom_toolbar()

    viewer = list(deconfigged_helper._app.get_viewers_of_cls('ImvizImageView'))[0]
    footprints = [m for m in viewer.figure.marks if isinstance(m, RegionOverlay)]
    assert len(footprints) == 3

    class MockTool:
        def __init__(self, viewer):
            self.viewer = viewer

    mock_tool = MockTool(viewer)

    # Get marks by label
    marks_by_label = {m.label: m for m in footprints}

    # Click inside first footprint (should select only obs1)
    m0_x, m0_y = np.mean(marks_by_label[0].x), np.mean(marks_by_label[0].y)
    msg_skewer = FootprintOverlayClickMessage(
        {'domain': {'x': m0_x, 'y': m0_y}},
        mode='skewer',
        sender=mock_tool
    )
    ldr._obj._on_region_select(msg_skewer)
    assert len(ldr._obj.observation_table.selected_rows) == 1
    assert ldr._obj.observation_table.selected_rows[0]['Dataset'] == 'obs1'

    # Ctrl+click inside second footprint - adds to selection
    m1_x, m1_y = np.mean(marks_by_label[1].x), np.mean(marks_by_label[1].y)
    msg_ctrl = FootprintOverlayClickMessage(
        {'domain': {'x': m1_x, 'y': m1_y}, 'ctrlKey': True},
        mode='skewer',
        sender=mock_tool
    )
    ldr._obj._on_region_select(msg_ctrl)
    assert len(ldr._obj.observation_table.selected_rows) == 2
    selected_datasets = {row['Dataset'] for row in ldr._obj.observation_table.selected_rows}
    assert selected_datasets == {'obs1', 'obs2'}

    # Ctrl+click inside third footprint - adds to selection
    m2_x, m2_y = np.mean(marks_by_label[2].x), np.mean(marks_by_label[2].y)
    msg_ctrl2 = FootprintOverlayClickMessage(
        {'domain': {'x': m2_x, 'y': m2_y}, 'ctrlKey': True},
        mode='skewer',
        sender=mock_tool
    )
    ldr._obj._on_region_select(msg_ctrl2)
    assert len(ldr._obj.observation_table.selected_rows) == 3
    selected_datasets = {row['Dataset'] for row in ldr._obj.observation_table.selected_rows}
    assert selected_datasets == {'obs1', 'obs2', 'obs3'}

    # Ctrl+click inside first footprint again - removes it from selection
    msg_ctrl_deselect = FootprintOverlayClickMessage(
        {'domain': {'x': m0_x, 'y': m0_y}, 'ctrlKey': True},
        mode='skewer',
        sender=mock_tool
    )
    ldr._obj._on_region_select(msg_ctrl_deselect)
    assert len(ldr._obj.observation_table.selected_rows) == 2
    selected_datasets = {row['Dataset'] for row in ldr._obj.observation_table.selected_rows}
    assert selected_datasets == {'obs2', 'obs3'}

    # Click outside all footprints - deselects all
    outside_x = 337.495
    outside_y = -20.835
    msg_outside = FootprintOverlayClickMessage(
        {'domain': {'x': outside_x, 'y': outside_y}},
        mode='skewer',
        sender=mock_tool
    )
    ldr._obj._on_region_select(msg_outside)
    assert len(ldr._obj.observation_table.selected_rows) == 0


def test_footprint_selection_skewer_overlapping(deconfigged_helper, image_nddata_wcs):
    """Test skewer mode with overlapping footprints and modifier key interactions."""
    deconfigged_helper.load(image_nddata_wcs, format='Image', data_label='test_image')

    table = Table()
    table['Dataset'] = ['obs1', 'obs2', 'obs3']
    # Create simple overlapping footprints - all three overlap in center
    table['s_region'] = [
        'POLYGON 337.498 -20.832 337.506 -20.832 337.506 -20.828 337.498 -20.828',
        'POLYGON 337.499 -20.831 337.505 -20.831 337.505 -20.829 337.499 -20.829',
        'POLYGON 337.500 -20.8305 337.504 -20.8305 337.504 -20.8295 337.500 -20.8295'
    ]

    ldr = deconfigged_helper.loaders['object']
    ldr.object = table
    ldr.treat_table_as_query = True
    ldr._obj.vue_link_by_wcs()
    ldr._obj.toggle_custom_toolbar()

    viewer = list(deconfigged_helper._app.get_viewers_of_cls('ImvizImageView'))[0]
    footprints = [m for m in viewer.figure.marks if isinstance(m, RegionOverlay)]
    assert len(footprints) == 3

    class MockTool:
        def __init__(self, viewer):
            self.viewer = viewer

    mock_tool = MockTool(viewer)

    marks_by_label = {m.label: m for m in footprints}

    # Use center of smallest footprint (obs3) which should be inside all 3
    m2_x, m2_y = np.mean(marks_by_label[2].x), np.mean(marks_by_label[2].y)

    msg_overlap = FootprintOverlayClickMessage(
        {'domain': {'x': m2_x, 'y': m2_y}},
        mode='skewer',
        sender=mock_tool
    )
    ldr._obj._on_region_select(msg_overlap)
    assert len(ldr._obj.observation_table.selected_rows) == 3
    selected_datasets = {row['Dataset'] for row in ldr._obj.observation_table.selected_rows}
    assert selected_datasets == {'obs1', 'obs2', 'obs3'}

    # Ctrl+click in the same overlapping region - should deselect all 3
    msg_ctrl_deselect_all = FootprintOverlayClickMessage(
        {'domain': {'x': m2_x, 'y': m2_y}, 'ctrlKey': True},
        mode='skewer',
        sender=mock_tool
    )
    ldr._obj._on_region_select(msg_ctrl_deselect_all)
    assert len(ldr._obj.observation_table.selected_rows) == 0

    # Click in a point inside obs1 and obs2 but outside obs3
    m1_x, m1_y = np.mean(marks_by_label[1].x), np.mean(marks_by_label[1].y)
    # Offset slightly towards edge to be outside obs3
    partial_x = m1_x + (marks_by_label[1].x[0] - m1_x) * 0.5
    partial_y = m1_y + (marks_by_label[1].y[0] - m1_y) * 0.5

    msg_partial = FootprintOverlayClickMessage(
        {'domain': {'x': partial_x, 'y': partial_y}},
        mode='skewer',
        sender=mock_tool
    )
    ldr._obj._on_region_select(msg_partial)
    # Should select obs1 and obs2
    assert len(ldr._obj.observation_table.selected_rows) >= 1  # At least obs2
    selected_datasets = {row['Dataset'] for row in ldr._obj.observation_table.selected_rows}

    # Ctrl+click in center (full overlap) - should add missing observations
    msg_ctrl_add = FootprintOverlayClickMessage(
        {'domain': {'x': m2_x, 'y': m2_y}, 'ctrlKey': True},
        mode='skewer',
        sender=mock_tool
    )
    ldr._obj._on_region_select(msg_ctrl_add)
    assert len(ldr._obj.observation_table.selected_rows) == 3
    selected_datasets = {row['Dataset'] for row in ldr._obj.observation_table.selected_rows}
    assert selected_datasets == {'obs1', 'obs2', 'obs3'}

    # Ctrl+click in center again - should deselect all 3
    msg_ctrl_remove = FootprintOverlayClickMessage(
        {'domain': {'x': m2_x, 'y': m2_y}, 'ctrlKey': True},
        mode='skewer',
        sender=mock_tool
    )
    ldr._obj._on_region_select(msg_ctrl_remove)
    assert len(ldr._obj.observation_table.selected_rows) == 0


def test_treat_table_as_query_toggle_keeps_switch_visible(deconfigged_helper):
    """
    Test that toggling treat_table_as_query off keeps parsed_input_is_query=True.
    This ensures the treat_table_as_query switch remains visible in the UI.
    """
    table = Table()
    table['Dataset'] = ['obs1', 'obs2']
    table['url'] = ['https://example.com/obs1.fits',
                    'https://example.com/obs2.fits']

    ldr = deconfigged_helper.loaders['object']
    ldr.object = table
    ldr.treat_table_as_query = True

    # Verify initial state
    assert ldr._obj.treat_table_as_query is True
    assert ldr._obj.parsed_input_is_query is True
    assert ldr._obj.file_table_populated is True

    # Toggle treat_table_as_query off
    ldr.treat_table_as_query = False

    # Verify that parsed_input_is_query remains True so the switch stays visible
    assert ldr._obj.treat_table_as_query is False
    assert ldr._obj.parsed_input_is_query is True
    # Tables should be hidden
    assert ldr._obj.file_table_populated is False
    assert ldr._obj.observation_table_populated is False

    # Toggle treat_table_as_query back on
    ldr.treat_table_as_query = True

    # Verify that tables are shown again
    assert ldr._obj.treat_table_as_query is True
    assert ldr._obj.parsed_input_is_query is True
    assert ldr._obj.file_table_populated is True


@pytest.mark.remote_data
def test_load_by_s3_uri(deconfigged_helper):
    s3_uri = "s3://stpubdata/jwst/public/jw02727/L3/t/o002/jw02727-o002_t062_nircam_clear-f277w_i2d.fits"  # noqa: E501

    # expected failure since this could be an image or catalog
    match = "Multiple valid loaders found for input."
    with pytest.raises(ValueError, match=match):
        deconfigged_helper.load(s3_uri)

    # no expected error:
    deconfigged_helper.load(s3_uri, format='Image')


class TestIsValid:
    """
    Tests for is_valid behavior across resolvers, parsers, and importers
    during load operations with mismatched formats.
    """

    @pytest.mark.parametrize(
        ('data_fixture', 'wrong_format'), [
            ('image_2d_wcs', '1D Spectrum'),
            ('image_2d_wcs', '3D Spectrum'),
            ('spectrum1d', 'Image'),
            ('spectrum1d', '3D Spectrum'),
            ('spectrum1d_cube', '1D Spectrum'),
            ('spectrum1d_cube', 'Image'),
        ])
    def test_load_data_as_wrong_format(self,
                                       data_fixture, wrong_format, deconfigged_helper, request):
        """
        Check loading data with a mismatched format.
        """
        with pytest.raises(ValueError,
                           match=rf'(?s)No valid loaders found for input.*{wrong_format}'):
            deconfigged_helper.load(request.getfixturevalue(data_fixture), format=wrong_format)

    def test_load_nonexistent_format(self, deconfigged_helper, image_2d_wcs):
        """
        Check loading a nonexistent file.
        """
        with pytest.raises(ValueError, match='No valid loaders found for input.'):
            deconfigged_helper.load(image_2d_wcs, format='fake format')

    def test_load_nonexistent_file(self, deconfigged_helper):
        """
        Check loading a nonexistent file.
        """
        with pytest.raises(ValueError, match='No valid loaders found for input.'):
            deconfigged_helper.load('this_file_does_not_exist.fits')
