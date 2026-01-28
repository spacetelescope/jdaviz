from jdaviz.app import Application
from jdaviz.core.loaders.resolvers.resolver import BaseResolver, find_closest_polygon_mark
from jdaviz.core.marks import RegionOverlay
from jdaviz.utils import find_polygon_mark_with_skewer

import numpy as np
from astropy.table import Table


# Create a minimal test class that mimics the resolver behavior
# without this we get an error when attempting to use BaseResolver directly
class TestBaseResolver(BaseResolver):
    template = ''

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


def test_server_is_remote_callback():
    # Create app instance
    app = Application()

    # Test the sync
    test_obj = TestBaseResolver(app=app)
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
    viewer = list(deconfigged_helper.app._viewer_store.values())[0]
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
    viewer = list(deconfigged_helper.app._viewer_store.values())[0]
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

    viewer = list(deconfigged_helper.app._viewer_store.values())[0]
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
    viewer = list(deconfigged_helper.app._viewer_store.values())[0]
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
    assert len(deconfigged_helper.app.data_collection) == 0
    assert ldr._obj.observation_table_populated is True
    assert ldr._obj.image_data_loaded is False


def test_footprint_with_image_deconfigged(deconfigged_helper, image_nddata_wcs):
    deconfigged_helper.load(image_nddata_wcs, format='Image', data_label='Test Image')
    assert len(deconfigged_helper.app.data_collection) == 1

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
    viewer = list(deconfigged_helper.app._viewer_store.values())[0]
    footprints = [m for m in viewer.figure.marks if isinstance(m, RegionOverlay)]
    assert len(footprints) == 1
    assert footprints[0].label == 0


def test_multiviewer_footprints(deconfigged_helper, image_nddata_wcs):
    deconfigged_helper.load(image_nddata_wcs, format='Image', data_label='Image 1')
    viewer = list(deconfigged_helper.app._viewer_store.values())[0]

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
    viewer = list(deconfigged_helper.app._viewer_store.values())[0]

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
    viewer = list(deconfigged_helper.app._viewer_store.values())[0]
    ldr._obj.custom_toolbar_enabled = True
    ldr._obj._add_footprints_to_viewer(viewer)

    # Assert footprints were added
    viewer_footprints = [m for m in viewer.figure.marks if isinstance(m, RegionOverlay)]
    assert len(viewer_footprints) == 1
    assert viewer_footprints[0].label == 0


def test_remove_footprints_from_viewer(deconfigged_helper, image_nddata_wcs):
    deconfigged_helper.load(image_nddata_wcs, format='Image', data_label='Image 1')
    viewer = list(deconfigged_helper.app._viewer_store.values())[0]

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

    viewer = list(deconfigged_helper.app._viewer_store.values())[0]
    footprints = [m for m in viewer.figure.marks if isinstance(m, RegionOverlay)]
    assert len(footprints) == 1

    # Get center of footprint (should be inside)
    mark = footprints[0]
    center_x = np.mean(mark.x)
    center_y = np.mean(mark.y)

    # Test skewer selection finds the footprint when clicking inside
    idx = find_polygon_mark_with_skewer(center_x, center_y, viewer, footprints)
    assert idx == 0

    # Test clicking outside footprint (using a point far away)
    far_x = mark.x[0] - 1000
    far_y = mark.y[0] - 1000
    idx_outside = find_polygon_mark_with_skewer(far_x, far_y, viewer, footprints)
    assert idx_outside is None


def test_skewer_selection_smallest_footprint(deconfigged_helper, image_nddata_wcs):
    """Test that skewer selection picks smallest footprint when multiple contain the click."""
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

    viewer = list(deconfigged_helper.app._viewer_store.values())[0]
    footprints = [m for m in viewer.figure.marks if isinstance(m, RegionOverlay)]
    assert len(footprints) == 2

    # Find the small footprint's center
    small_mark = [m for m in footprints if m.label == 1][0]
    center_x = np.mean(small_mark.x)
    center_y = np.mean(small_mark.y)

    # Click in the center of small footprint (which is also inside large)
    # Should select the smaller one (label 1)
    idx = find_polygon_mark_with_skewer(center_x, center_y, viewer, footprints)
    assert idx == 1


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

    viewer = list(deconfigged_helper.app._viewer_store.values())[0]
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

    viewer = list(deconfigged_helper.app._viewer_store.values())[0]
    footprints = [m for m in viewer.figure.marks if isinstance(m, RegionOverlay)]
    # Only one footprint should be created (second one is empty)
    assert len(footprints) == 1

    mark = footprints[0]
    center_x = np.mean(mark.x)
    center_y = np.mean(mark.y)

    # Should still work with the single valid footprint
    idx = find_polygon_mark_with_skewer(center_x, center_y, viewer, footprints)
    assert idx == 0
