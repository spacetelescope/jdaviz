import pytest
import numpy as np
from numpy.testing import assert_allclose
from regions import RectanglePixelRegion


def test_spectrum_at_spaxel_no_alt(cubeviz_helper, spectrum1d_cube_with_uncerts):
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

    assert_allclose(spectrum_viewer.get_limits(), (4.6228e-07, 4.6236e-07, 28, 92))

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

    assert_allclose(spectrum_viewer.get_limits(),
                    (4.6228e-07, 4.6236e-07, 4, 15.6))  # Zoomed to spaxel
    spectrum_viewer.set_limits(
        x_min=4.623e-07, x_max=4.6232e-07, y_min=42, y_max=88)  # Zoom in X and Y

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

    # Check that zoom in both X and Y is kept.
    assert_allclose(spectrum_viewer.get_limits(), (4.623e-07, 4.6232e-07, 42, 88))

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


@pytest.mark.parametrize("cube_type", ["Surface Brightness", "Flux"])
def test_spectrum_at_spaxel_altkey_true(cubeviz_helper, spectrum1d_cube,
                                        spectrum1d_cube_sb_unit, cube_type):

    # test is parameterize to test a cube that is in Jy / sr (Surface Brightness)
    # as well as Jy (Flux), to test that flux cubes, which are converted in the
    # parser to flux / pix^2 surface brightness cubes, both work correctly.

    if cube_type == 'Surface Brightness':
        cube = spectrum1d_cube_sb_unit
        cube_unit = 'Jy / sr'
    elif cube_type == 'Flux':
        cube = spectrum1d_cube
        cube_unit = 'Jy / pix2'

    cubeviz_helper.load_data(cube, data_label='test')

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
                                        {'event': 'mousemove', 'domain': {'x': 2, 'y': 1}})
    assert label_mouseover.as_text() == (f'Pixel x=02.0 y=01.0 Value +1.40000e+01 {cube_unit}',
                                         'World 13h39m59.9192s +27d00m00.7200s (ICRS)',
                                         '204.9996633015 27.0001999996 (deg)')

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
    x = 0
    y = 0
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
    assert label_mouseover.as_text() == (f'Pixel x=01.0 y=01.0 Value +1.30000e+01 {cube_unit}',
                                         'World 13h39m59.9461s +27d00m00.7200s (ICRS)',
                                         '204.9997755344 27.0001999998 (deg)')

    # Make sure linked pan mode works on all image viewers
    t_linkedpan = flux_viewer.toolbar.tools['jdaviz:pixelpanzoommatch']
    t_linkedpan.activate()
    # TODO: When Cubeviz uses Astrowidgets, can just use center_on() for this part.
    flux_viewer.set_limits(x_min=20, x_max=40, y_min=15, y_max=35)
    v = uncert_viewer
    assert v.state.zoom_center_x == flux_viewer.state.zoom_center_x
    assert v.state.zoom_center_y == flux_viewer.state.zoom_center_y
    assert v.state.zoom_radius == flux_viewer.state.zoom_radius
    t_linkedpan.deactivate()


def test_spectrum_at_spaxel_with_2d(cubeviz_helper):
    # Use cube with single slice
    x = np.array([[[1, 2, 3], [4, 5, 6]]])

    cubeviz_helper.load_data(x, data_label='test')

    flux_viewer = cubeviz_helper.app.get_viewer("flux-viewer")
    spectrum_viewer = cubeviz_helper.app.get_viewer("spectrum-viewer")

    # Set the active tool to spectrumperspaxel
    flux_viewer.toolbar.active_tool = flux_viewer.toolbar.tools['jdaviz:spectrumperspaxel']
    x = 0
    y = 0
    assert len(flux_viewer.native_marks) == 2
    assert len(spectrum_viewer.data()) == 1  # Spectrum (sum)

    # Click on spaxel location
    flux_viewer.toolbar.active_tool.on_mouse_event(
        {'event': 'click', 'domain': {'x': x, 'y': y}, 'altKey': False})
    assert len(flux_viewer.native_marks) == 3
    assert len(spectrum_viewer.data()) == 2  # Spectrum (sum), Spectrum (Subset 1, sum)

    # Deselect tool
    flux_viewer.toolbar.active_tool = None
    assert len(flux_viewer.native_marks) == 3
