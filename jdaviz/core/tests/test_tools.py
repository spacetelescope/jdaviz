from numpy.testing import assert_allclose


def test_boxzoom(cubeviz_helper, image_cube_hdu_obj_microns):
    cubeviz_helper.load_data(image_cube_hdu_obj_microns, data_label="Test Flux")

    flux_viewer = cubeviz_helper.app.get_viewer('flux-viewer')

    assert flux_viewer.state.y_min == -0.5
    assert flux_viewer.state.y_max == 8.5
    assert flux_viewer.state.x_min == -0.5
    assert flux_viewer.state.x_max == 9.5

    t = flux_viewer.toolbar.tools['jdaviz:boxzoom']
    t.activate()
    t.interact.selected_x = [1, 4]
    t.interact.selected_y = [2, 6]

    assert_allclose(t.get_x_axis_with_aspect_ratio(), [0.277778, 4.722222], rtol=1e-6)
