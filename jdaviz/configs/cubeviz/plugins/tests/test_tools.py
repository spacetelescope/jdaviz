import pytest
from astropy.nddata import CCDData
from echo import delay_callback
from regions import RectanglePixelRegion


@pytest.mark.filterwarnings('ignore:No observer defined on WCS')
def test_spectrum_at_spaxel(cubeviz_helper, spectrum1d_cube):
    cubeviz_helper.load_data(spectrum1d_cube, data_label='test')

    flux_viewer = cubeviz_helper.app.get_viewer("flux-viewer")
    spectrum_viewer = cubeviz_helper.app.get_viewer("spectrum-viewer")

    # Set the active tool to spectrumperspaxel
    flux_viewer.toolbar.active_tool = flux_viewer.toolbar.tools['jdaviz:spectrumperspaxel']
    x = 1
    y = 1
    assert len(flux_viewer.native_marks) == 2
    assert len(spectrum_viewer.data()) == 1

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

    # Deselect tool
    flux_viewer.toolbar.active_tool = None
    assert len(flux_viewer.native_marks) == 3


def test_spectrum_at_spaxel_altkey_true(cubeviz_helper, spectrum1d_cube):
    cubeviz_helper.load_data(spectrum1d_cube, data_label='test')

    flux_viewer = cubeviz_helper.app.get_viewer("flux-viewer")
    uncert_viewer = cubeviz_helper.app.get_viewer("uncert-viewer")
    spectrum_viewer = cubeviz_helper.app.get_viewer("spectrum-viewer")

    # Set the active tool to spectrumperspaxel
    flux_viewer.toolbar.active_tool = flux_viewer.toolbar.tools['jdaviz:spectrumperspaxel']
    x = 1
    y = 1
    assert len(flux_viewer.native_marks) == 2
    assert len(spectrum_viewer.data()) == 1

    # Check coordinate info panel
    label_mouseover = cubeviz_helper.app.session.application._tools['g-coords-info']
    label_mouseover._viewer_mouse_event(flux_viewer,
                                        {'event': 'mousemove', 'domain': {'x': 1, 'y': 1}})
    assert label_mouseover.as_text() == ('Pixel x=01.0 y=01.0 Value +1.30000e+01 Jy',
                                         'World 13h39m59.9461s +27d00m00.7200s (ICRS)',
                                         '204.9997755344 27.0001999998 (deg)')

    # Click on spaxel location
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
    t_linkedpan = flux_viewer.toolbar.tools['jdaviz:simplepanzoommatch']
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
