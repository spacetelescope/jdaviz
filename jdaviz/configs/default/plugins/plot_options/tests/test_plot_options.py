import pytest
import numpy as np
from numpy import allclose
from numpy.testing import assert_allclose
from photutils.datasets import make_4gaussians_image
from astropy.nddata import NDData
from astropy import units as u
from jdaviz.configs.default.plugins.plot_options.plot_options import SplineStretch


@pytest.mark.filterwarnings('ignore')
def test_multiselect(cubeviz_helper, spectrum1d_cube):
    cubeviz_helper.load_data(spectrum1d_cube)
    po = cubeviz_helper.app.get_tray_item_from_name('g-plot-options')

    # default selection for viewer should be flux-viewer (first in list) and nothing for layer
    assert po.multiselect is False
    assert po.viewer.multiselect is False
    assert po.layer.multiselect is False
    assert po.viewer.selected == 'flux-viewer'
    assert po.layer.selected == 'Unknown spectrum object[FLUX]'

    po.multiselect = True
    assert po.viewer.multiselect is True
    assert po.layer.multiselect is True

    po.viewer.selected = ['flux-viewer', 'uncert-viewer']
    # any internal call to reset the defaults (due to a change in the choices by adding or removing
    # a viewer, etc) should not reset the selection
    po.viewer._apply_default_selection(skip_if_current_valid=True)
    assert po.viewer.selected == ['flux-viewer', 'uncert-viewer']

    # from API could call po.axes_visible.value = False, but we'll also test the vue-level wrapper
    po.vue_set_value({'name': 'axes_visible_value', 'value': False})
    assert po.axes_visible.value is False

    for viewer_name in ['flux-viewer', 'uncert-viewer']:
        assert cubeviz_helper.app.get_viewer(viewer_name).state.show_axes is False

    assert cubeviz_helper.app.get_viewer('spectrum-viewer').state.show_axes is True
    assert po.axes_visible.sync['mixed'] is False

    # adding another viewer should show a mixed-state
    po.viewer.selected = ['flux-viewer', 'uncert-viewer', 'spectrum-viewer']
    # spectrum viewer is excluded from the axes_visible/show_axes logic
    assert len(po.axes_visible.linked_states) == 2
    assert len(po.axes_visible.sync['icons']) == 2
    assert po.axes_visible.sync['mixed'] is False

    # from API could call po.axes_visible.unmix_state, but we'll also test the vue-level wrapper
    po.vue_unmix_state('axes_visible')
    assert po.axes_visible.sync['mixed'] is False
    assert po.axes_visible.value is False

    for viewer_name in ['flux-viewer', 'uncert-viewer']:
        assert cubeviz_helper.app.get_viewer(viewer_name).state.show_axes is False

    for viewer_name in ['spectrum-viewer']:
        assert cubeviz_helper.app.get_viewer(viewer_name).state.show_axes is True

    po.multiselect = False
    # should default back to the first selected entry
    assert po.viewer.multiselect is False
    assert po.viewer.selected == 'flux-viewer'
    assert po.axes_visible.value is False

    po.viewer.selected = 'spectrum-viewer'
    assert po.axes_visible.sync['in_subscribed_states'] is False
    assert len(po.axes_visible.linked_states) == 0


@pytest.mark.filterwarnings('ignore')
def test_stretch_histogram(cubeviz_helper, spectrum1d_cube_with_uncerts):
    cubeviz_helper.load_data(spectrum1d_cube_with_uncerts)
    po = cubeviz_helper.app.get_tray_item_from_name('g-plot-options')
    po.plugin_opened = True

    assert po.stretch_histogram is not None

    hist_lyr = po.stretch_histogram.layers['histogram']
    flux_cube_sample = hist_lyr.layer.data['x']

    # changing viewer should change results
    po.viewer.selected = 'uncert-viewer'
    assert not allclose(hist_lyr.layer.data['x'], flux_cube_sample)

    po.viewer.selected = 'flux-viewer'
    assert_allclose(hist_lyr.layer.data['x'], flux_cube_sample)

    # change viewer limits
    fv = cubeviz_helper.app.get_viewer('flux-viewer')
    fv.state.x_max = 0.5 * fv.state.x_max
    # viewer limits should not be affected by default
    # (re-retrieve layer - it should not have changed)
    hist_lyr = po.stretch_histogram.layers['histogram']
    assert_allclose(hist_lyr.layer.data['x'], flux_cube_sample)

    # set to listen to viewer limits, the length of the samples will change
    # (in this case the layer itself has been replaced)
    po.stretch_hist_zoom_limits = True
    hist_lyr = po.stretch_histogram.layers['histogram']
    assert len(hist_lyr.layer.data['x']) != len(flux_cube_sample)

    po.stretch_vmin.value = 0.5
    po.stretch_vmax.value = 1

    assert po.stretch_histogram.marks['vmin'].x[0] == po.stretch_vmin.value
    assert po.stretch_histogram.marks['vmax'].x[0] == po.stretch_vmax.value

    assert po.stretch_histogram.viewer.state.hist_n_bin == 25
    po.stretch_hist_nbins = 20
    assert po.stretch_histogram.viewer.state.hist_n_bin == 20

    po.set_histogram_limits(x_min=0.25, x_max=2)
    assert po.stretch_histogram.viewer.state.x_min == 0.25
    assert po.stretch_histogram.viewer.state.x_max == 2

    po.set_histogram_limits(y_min=1, y_max=2)
    assert po.stretch_histogram.viewer.state.y_min == 1
    assert po.stretch_histogram.viewer.state.y_max == 2

    assert po.stretch_histogram.marks['vmin'].x[0] == po.stretch_vmin.value
    assert po.stretch_histogram.marks['vmax'].x[0] == po.stretch_vmax.value


@pytest.mark.filterwarnings('ignore')
def test_user_api(cubeviz_helper, spectrum1d_cube):
    cubeviz_helper.load_data(spectrum1d_cube)
    po = cubeviz_helper.plugins['Plot Options']

    assert po.multiselect is False
    assert "multiselect" in po.viewer.__repr__()

    # regression test for https://github.com/spacetelescope/jdaviz/pull/1708
    # user calls to select_default should revert even if current entry is valid
    po.viewer = 'spectrum-viewer'
    assert po.viewer.selected == 'spectrum-viewer'
    po.viewer.select_default()
    assert po.viewer.selected == 'flux-viewer'

    po.select_all()
    assert po.multiselect is True
    assert len(po.viewer.selected) == 3

    po.viewer.select_none()
    assert len(po.viewer.selected) == 0

    po.viewer.select_default()
    po.layer.select_default()
    assert po.multiselect is True
    assert len(po.viewer.selected) == 1
    assert len(po.layer.selected) == 1

    with pytest.raises(ValueError):
        po.viewer = ['flux-viewer', 'invalid-viewer']

    assert len(po.viewer.selected) == 1

    po.viewer = 'flux-viewer'
    po.layer.select_all()

    # check a plot option with and without choices
    assert hasattr(po.stretch_preset, 'choices')
    assert len(po.stretch_preset.choices) > 1
    assert "choices" in po.stretch_preset.__repr__()
    assert not hasattr(po.image_contrast, 'choices')
    assert "choices" not in po.image_contrast.__repr__()

    # try setting with both label and value
    po.stretch_preset = 90
    po.stretch_preset = 'Min/Max'

    # try eq on both text and value
    assert po.image_colormap == 'gray'
    assert po.image_colormap == 'Gray'

    # toggle contour (which has a spinner implemented)
    po.contour_visible = True
    assert po._obj.contour_spinner is False


def test_stretch_spline(imviz_helper):
    image_1 = NDData(make_4gaussians_image(), unit=u.nJy)
    # Load the test data into imviz
    imviz_helper.load_data(image_1)
    po = imviz_helper.plugins['Plot Options']

    # Configure initial stretch options and select "Spline" function
    with po.as_active():
        po.stretch_vmin.value = 10
        po.stretch_vmax.value = 100
        po.stretch_curve_visible = True
        po.stretch_function = "Spline"

    # Retrieve knots data from the generated histogram
    scatter_obj = po._obj.stretch_histogram.marks["stretch_knots: NDData[DATA] (DATA)"]
    knots_x = scatter_obj.x
    knots_y = scatter_obj.y

    # Expected knots based on initial stretch settings
    expected_x = [10., 19., 28., 73., 100.]
    expected_y = [0., 0.05, 0.3, 0.9, 1.]

    # Validate if the generated knots match the expected knots
    np.testing.assert_allclose(knots_x, expected_x)
    np.testing.assert_allclose(knots_y, expected_y)

    # Update the stretch options to new values and verify the knots update correctly
    with po.as_active():
        po.stretch_vmin.value = 10
        po.stretch_vmax.value = 80
        po.stretch_curve_visible = True
        po.stretch_function = "Spline"

    knots_x = scatter_obj.x

    # Expected knots based on updated stretch settings
    expected_x = [10., 17., 24., 59., 80.]
    expected_y = [0., 0.05, 0.3, 0.9, 1.]

    # Validate if the generated knots for updated settings match the expected values
    np.testing.assert_allclose(knots_x, expected_x)
    np.testing.assert_allclose(knots_y, expected_y)

    # Disable the stretch curve and ensure no knots or stretches are visible
    with po.as_active():
        po.stretch_curve_visible = False
    stretch_curve = po._obj.stretch_histogram.marks['stretch_curve: NDData[DATA] (DATA)']
    assert len(stretch_curve.y) == 0
    assert len(stretch_curve.x) == 0
    assert len(scatter_obj.x) == 0
    assert len(scatter_obj.x) == 0


def test_update_knots_mismatched_length():
    stretch = SplineStretch()
    with pytest.raises(ValueError):
        stretch.update_knots(x=[0, 0.1, 0.2], y=[0, 0.05])
