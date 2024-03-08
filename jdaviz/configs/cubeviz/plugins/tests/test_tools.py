import pytest
from astropy.nddata import CCDData
from echo import delay_callback
from regions import RectanglePixelRegion


@pytest.mark.filterwarnings('ignore:No observer defined on WCS')
def test_spectrum_at_spaxel(cubeviz_helper, spectrum1d_cube_with_uncerts):
    cubeviz_helper.load_data(spectrum1d_cube_with_uncerts, data_label='test')

    flux_viewer = cubeviz_helper.app.get_viewer("flux-viewer")
    uncert_viewer = cubeviz_helper.app.get_viewer("uncert-viewer")
    spectrum_viewer = cubeviz_helper.app.get_viewer("spectrum-viewer")

    # Set the active tool to spectrumperspaxel
    flux_viewer.toolbar.active_tool = flux_viewer.toolbar.tools['jdaviz:spectrumperspaxel']
    x = 1
    y = 1
    assert len(flux_viewer.native_marks) == 2
    assert len(spectrum_viewer.data()) == 1

    # Move to spaxel location
    flux_viewer.toolbar.active_tool.on_mouse_move(
        {'event': 'mousemove', 'domain': {'x': x, 'y': y}, 'altKey': False})
    assert flux_viewer.toolbar.active_tool._mark in spectrum_viewer.figure.marks
    assert flux_viewer.toolbar.active_tool._mark.visible is True

    # Click on spaxel location
    flux_viewer.toolbar.active_tool.on_mouse_event(
        {'event': 'click', 'domain': {'x': x, 'y': y}, 'altKey': False})
    assert len(flux_viewer.native_marks) == 3
    assert len(spectrum_viewer.data()) == 2

    # Check that a new subset was created
    subsets = cubeviz_helper.app.get_subsets()
    reg = subsets.get('Subset 1')[0]['region']
    assert len(subsets) == 1
    assert isinstance(reg, RectanglePixelRegion)

    # Move out of bounds
    flux_viewer.toolbar.active_tool.on_mouse_move(
        {'event': 'mousemove', 'domain': {'x': -1, 'y': -1}, 'altKey': False})
    assert flux_viewer.toolbar.active_tool._mark.visible is False

    # Mouse leave event
    flux_viewer.toolbar.active_tool.on_mouse_move(
        {'event': 'mouseleave', 'domain': {'x': x, 'y': y}, 'altKey': False})
    assert flux_viewer.toolbar.active_tool._mark.visible is False

    # Deselect tool
    flux_viewer.toolbar.active_tool = None
    assert len(flux_viewer.native_marks) == 3

    # Check in uncertainty viewer as well. Set mouseover here
    cubeviz_helper.app.session.application._tools['g-coords-info'].dataset.selected = 'none'
    uncert_viewer.toolbar.active_tool = uncert_viewer.toolbar.tools['jdaviz:spectrumperspaxel']
    uncert_viewer.toolbar.active_tool.on_mouse_move(
        {'event': 'mousemove', 'domain': {'x': x, 'y': y}, 'altKey': False})
    assert uncert_viewer.toolbar.active_tool._mark in spectrum_viewer.figure.marks
    assert uncert_viewer.toolbar.active_tool._mark.visible is True

    # Select specific data
    cubeviz_helper.app.session.application._tools['g-coords-info'].dataset.selected = 'test[FLUX]'
    uncert_viewer.toolbar.active_tool = uncert_viewer.toolbar.tools['jdaviz:spectrumperspaxel']
    uncert_viewer.toolbar.active_tool.on_mouse_move(
        {'event': 'mousemove', 'domain': {'x': x, 'y': y}, 'altKey': False})
    assert uncert_viewer.toolbar.active_tool._mark in spectrum_viewer.figure.marks
    assert uncert_viewer.toolbar.active_tool._mark.visible is True


def test_spectrum_at_spaxel_altkey_true(cubeviz_helper, spectrum1d_cube):
    cubeviz_helper.load_data(spectrum1d_cube, data_label='test')

    flux_viewer = cubeviz_helper.app.get_viewer("flux-viewer")
    uncert_viewer = cubeviz_helper.app.get_viewer("uncert-viewer")
    spectrum_viewer = cubeviz_helper.app.get_viewer("spectrum-viewer")

    # Set the active tool to spectrumperspaxel
    flux_viewer.toolbar.active_tool = flux_viewer.toolbar.tools['jdaviz:spectrumperspaxel']

    assert len(flux_viewer.native_marks) == 2
    assert len(spectrum_viewer.data()) == 1

    # Check coordinate info panel
    sl = cubeviz_helper.plugins['Slice']
    sl.value = sl._obj.valid_indicator_values_sorted[1]
    assert flux_viewer.slice == 1
    label_mouseover = cubeviz_helper.app.session.application._tools['g-coords-info']
    label_mouseover._viewer_mouse_event(flux_viewer,
                                        {'event': 'mousemove', 'domain': {'x': 1, 'y': 1}})
    assert label_mouseover.as_text() == ('Pixel x=01.0 y=01.0 Value +1.30000e+01 Jy',
                                         'World 13h39m59.9461s +27d00m00.7200s (ICRS)',
                                         '204.9997755344 27.0001999998 (deg)')

    # Click on spaxel location
    x = 1
    y = 1
    flux_viewer.toolbar.active_tool.on_mouse_event(
        {'event': 'click', 'domain': {'x': x, 'y': y}, 'altKey': False})
    assert len(flux_viewer.native_marks) == 3
    assert len(spectrum_viewer.data()) == 2

    # Check that subset was created
    subsets = cubeviz_helper.app.get_subsets()
    reg = subsets.get('Subset 1')[0]['region']
    assert len(subsets) == 1
    assert isinstance(reg, RectanglePixelRegion)

    # Using altKey should create a new subset
    x = 2
    y = 2
    flux_viewer.toolbar.active_tool.on_mouse_event(
        {'event': 'click', 'domain': {'x': x, 'y': y}, 'altKey': True})
    assert len(flux_viewer.native_marks) == 4
    assert len(spectrum_viewer.data()) == 3

    subsets = cubeviz_helper.app.get_subsets()
    reg2 = subsets.get('Subset 2')[0]['region']
    assert len(subsets) == 2
    assert isinstance(reg2, RectanglePixelRegion)

    # Make sure coordinate info panel did not change
    label_mouseover._viewer_mouse_event(flux_viewer,
                                        {'event': 'mousemove', 'domain': {'x': 1, 'y': 1}})
    assert label_mouseover.as_text() == ('Pixel x=01.0 y=01.0 Value +1.30000e+01 Jy',
                                         'World 13h39m59.9461s +27d00m00.7200s (ICRS)',
                                         '204.9997755344 27.0001999998 (deg)')

    # Make sure linked pan mode works on all image viewers
    t_linkedpan = flux_viewer.toolbar.tools['jdaviz:pixelpanzoommatch']
    t_linkedpan.activate()
    # TODO: When Cubeviz uses Astrowidgets, can just use center_on() for this part.
    with delay_callback(flux_viewer.state, 'x_min', 'x_max', 'y_min', 'y_max'):
        flux_viewer.state.x_min = 20
        flux_viewer.state.y_min = 15
        flux_viewer.state.x_max = 40
        flux_viewer.state.y_max = 35
    v = uncert_viewer
    assert (v.state.x_min, v.state.x_max, v.state.y_min, v.state.y_max) == (20, 40, 15, 35)
    t_linkedpan.deactivate()


def test_spectrum_at_spaxel_with_2d(cubeviz_helper):
    # Use 2D image, which should not work with the tool
    x = CCDData([[1, 2, 3], [4, 5, 6]], unit='adu')

    app = cubeviz_helper.app
    app.data_collection["test"] = x
    app.add_data_to_viewer("flux-viewer", "test")

    flux_viewer = cubeviz_helper.app.get_viewer("flux-viewer")
    spectrum_viewer = cubeviz_helper.app.get_viewer("spectrum-viewer")

    # Set the active tool to spectrumperspaxel
    flux_viewer.toolbar.active_tool = flux_viewer.toolbar.tools['jdaviz:spectrumperspaxel']
    x = 1
    y = 1
    assert len(flux_viewer.native_marks) == 2
    assert len(spectrum_viewer.data()) == 0

    # Click on spaxel location
    flux_viewer.toolbar.active_tool.on_mouse_event(
        {'event': 'click', 'domain': {'x': x, 'y': y}, 'altKey': False})
    assert len(flux_viewer.native_marks) == 3
    assert len(spectrum_viewer.data()) == 0

    # Deselect tool
    flux_viewer.toolbar.active_tool = None
    assert len(flux_viewer.native_marks) == 3
