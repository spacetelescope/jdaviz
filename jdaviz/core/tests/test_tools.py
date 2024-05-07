import time
from astropy import units as u
from astropy.nddata import NDData
from photutils.datasets import make_4gaussians_image
import numpy as np
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


def _get_lims(viewer):
    return [viewer.state.x_min, viewer.state.x_max,
            viewer.state.y_min, viewer.state.y_max]


def test_rangezoom(specviz_helper, spectrum1d):
    specviz_helper.load_data(spectrum1d, data_label='test')

    sv = specviz_helper.app.get_viewer('spectrum-viewer')
    assert_allclose(_get_lims(sv), [6000, 8000, 12.30618014327326, 16.542560043585965])

    t = sv.toolbar.tools['jdaviz:xrangezoom']
    t.activate()
    t.interact.selected = [6500, 7000]
    t.on_update_zoom()
    assert_allclose(_get_lims(sv), [6500, 7000, 12.30618014327326, 16.542560043585965])

    t = sv.toolbar.tools['jdaviz:yrangezoom']
    t.activate()
    t.interact.selected = [14, 15]
    t.on_update_zoom()
    assert_allclose(_get_lims(sv), [6500, 7000, 14, 15])


def test_stretch_bounds(imviz_helper):
    imviz_helper.load_data(np.ones((2, 2)))

    plot_options = imviz_helper.plugins['Plot Options']._obj
    stretch_tool = plot_options.stretch_histogram.toolbar.tools["jdaviz:stretch_bounds"]
    plot_options.stretch_histogram.toolbar.active_tool = stretch_tool

    min_msg = {'event': 'click', 'pixel': {'x': 40, 'y': 322},
               'domain': {'x': 0.1, 'y': 342},
               'button': 0, 'altKey': False, 'ctrlKey': False, 'metaKey': False}

    max_msg = {'event': 'click', 'pixel': {'x': 40, 'y': 322},
               'domain': {'x': 1.3, 'y': 342},
               'button': 0, 'altKey': False, 'ctrlKey': False, 'metaKey': False}

    stretch_tool.on_mouse_event(min_msg)
    time.sleep(0.3)
    stretch_tool.on_mouse_event(max_msg)

    assert plot_options.stretch_vmin_value == 0.1
    assert plot_options.stretch_vmax_value == 1.3

    plot_options.stretch_histogram.toolbar.active_tool = None


def test_stretch_bounds_and_spline(imviz_helper):

    # As the histogram randomly samples the array, we should make sure the
    # values used here are reproducible
    np.random.seed(42)

    image_1 = NDData(make_4gaussians_image(), unit=u.nJy)
    imviz_helper.load_data(image_1)
    po = imviz_helper.plugins["Plot Options"]

    with po.as_active():
        po.stretch_vmin.value = 1
        po.stretch_vmax.value = 50
        po.stretch_curve_visible = True
        po.stretch_function = "Spline"
        stretch_tool = po._obj.stretch_histogram.toolbar.tools["jdaviz:stretch_bounds"]

        knot_move_msg = {
            "event": "dragmove",
            "pixel": {"x": 60.25, "y": 266.0078125},
            "domain": {"x": 11.639166666374734, "y": 970.9392968750001},
        }

        knots_after_drag_move = (
            [0.0, 0.1, 0.21712585033417825, 0.7, 1.0],
            [0.0, 0.05, 0.2852214046563617, 0.9, 1.0],
        )

        stretch_tool.on_mouse_event(knot_move_msg)

        assert po._obj.stretch_vmin_value == 1
        assert po._obj.stretch_vmax_value == 50
        assert np.allclose(po._obj.stretch_params_value["knots"], knots_after_drag_move)


def test_stretch_bounds_click_outside_threshold(imviz_helper):
    image_1 = NDData(make_4gaussians_image(), unit=u.nJy)
    imviz_helper.load_data(image_1)

    po = imviz_helper.plugins["Plot Options"]
    po = imviz_helper.plugins["Plot Options"]

    with po.as_active():
        po.stretch_function = "Spline"
        stretch_tool = po._obj.stretch_histogram.toolbar.tools["jdaviz:stretch_bounds"]

        # a click event just outside the threshold for moving a bound
        outside_threshold_msg = {
            "event": "click",
            "pixel": {"x": 40, "y": 322},
            "domain": {"x": 1.5, "y": 342},
            "button": 0, "altKey": False, "ctrlKey": False, "metaKey": False
        }

        initial_vmin = po.stretch_vmin.value
        initial_vmax = po.stretch_vmax.value

        stretch_tool.on_mouse_event(outside_threshold_msg)
        assert po.stretch_vmin.value == initial_vmin
        assert po.stretch_vmax.value == initial_vmax
