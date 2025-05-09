import numpy as np
import pytest
from astropy import units as u
from astropy.nddata import NDData
import matplotlib
from numpy.testing import assert_allclose
from photutils.datasets import make_4gaussians_image

from jdaviz.configs.default.plugins.plot_options.plot_options import SplineStretch


@pytest.mark.filterwarnings('ignore')
def test_multiselect(cubeviz_helper, spectrum1d_cube):
    cubeviz_helper.load_data(spectrum1d_cube)
    po = cubeviz_helper.app.get_tray_item_from_name('g-plot-options')

    # default selection for viewer should be flux-viewer (first in list) and nothing for layer
    assert po.viewer.multiselect is False
    assert po.layer.multiselect is False
    assert po.viewer.selected == 'flux-viewer'
    assert po.layer.selected == 'Unknown spectrum object[FLUX]'

    # deprecated functionality to toggle both at once, replace with setting
    # individually when removing
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

    po.viewer_multiselect = False
    # should default back to the first selected entry
    assert po.viewer.multiselect is False
    assert po.viewer.selected == 'flux-viewer'
    po.layer_multiselect = False
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

    # check the colorbar
    cb = po.stretch_histogram._marks["colorbar"]
    assert_allclose(cb.x, po.stretch_histogram.figure.marks[0].x)
    assert_allclose(cb.y, 1)
    assert cb.colors == [  # Gray scale, linear
        '#050505', '#0f0f0f', '#191919', '#232323', '#2e2e2e',
        '#383838', '#424242', '#4c4c4c', '#575757', '#616161',
        '#6b6b6b', '#757575', '#808080', '#8a8a8a', '#949494',
        '#9e9e9e', '#a8a8a8', '#b3b3b3', '#bdbdbd', '#c7c7c7',
        '#d1d1d1', '#dcdcdc', '#e6e6e6', '#f0f0f0', '#fafafa']

    hist_lyr = po.stretch_histogram.layers['histogram']
    flux_cube_sample = hist_lyr.layer.data['x']

    # changing viewer should change results
    po.viewer.selected = 'uncert-viewer'
    with pytest.raises(AssertionError):
        assert_allclose(hist_lyr.layer.data['x'], flux_cube_sample)

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

    # Make sure some tools work

    po_panzoom = po.stretch_histogram.toolbar.tools["jdaviz:panzoom"]
    po_panzoom.activate()
    po_panzoom.deactivate()

    po_prevzoom = po.stretch_histogram.toolbar.tools["jdaviz:prevzoom"]
    po_prevzoom.activate()


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
    assert "choices" in po.stretch_preset._obj.__repr__()
    assert not hasattr(po.image_contrast, 'choices')
    assert "choices" not in po.image_contrast._obj.__repr__()

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
    scatter_obj = po._obj.stretch_histogram.marks["stretch_knots"]
    knots_x = scatter_obj.x
    knots_y = scatter_obj.y

    # Expected knots based on initial stretch settings
    expected_x = [10., 19., 28., 73., 100.]
    expected_y = np.array([0., 0.05, 0.3, 0.9, 1.]) * 0.9  # rescaled to 0.9

    # Validate if the generated knots match the expected knots
    assert scatter_obj.visible
    assert_allclose(knots_x, expected_x)
    assert_allclose(knots_y, expected_y)

    # Update the stretch options to new values and verify the knots update correctly
    with po.as_active():
        po.stretch_vmin.value = 10
        po.stretch_vmax.value = 80
        po.stretch_function = "Spline"

    knots_x = scatter_obj.x
    knots_y = scatter_obj.y

    # Expected knots based on updated stretch settings
    expected_x = [10., 17., 24., 59., 80.]
    expected_y = np.array([0., 0.05, 0.3, 0.9, 1.]) * 0.9  # rescaled to 0.9

    # Validate if the generated knots for updated settings match the expected values
    assert scatter_obj.visible
    assert_allclose(knots_x, expected_x)
    assert_allclose(knots_y, expected_y)

    # Disable the stretch curve and ensure no knots or stretches are visible
    with po.as_active():
        po.stretch_curve_visible = False
    stretch_curve = po._obj.stretch_histogram.marks['stretch_curve']
    assert len(stretch_curve.y) == 0
    assert len(stretch_curve.x) == 0
    assert len(scatter_obj.x) == 0
    assert len(scatter_obj.x) == 0


def test_update_knots_mismatched_length():
    stretch = SplineStretch()
    with pytest.raises(ValueError):
        stretch.update_knots(x=[0, 0.1, 0.2], y=[0, 0.05])


def test_apply_presets(imviz_helper):
    arr = np.arange(36).reshape(6, 6)
    po = imviz_helper.plugins['Plot Options']

    preset_colors_4 = ["#0000ff", "#00ff00", po._obj.swatches_palette[1][0].lower(),
                       po._obj.swatches_palette[0][0].lower()]

    # Test applying presets with < 6 layers

    for i in range(4):
        imviz_helper.load_data(arr, data_label=f"array_{i}")

    po.image_color_mode = "Color"
    po.apply_RGB_presets()

    for i in range(4):
        po.layer = f"array_{i}"
        assert po.stretch_function.value == "arcsinh"
        assert po.stretch_preset.value == 99
        assert po.image_color.value == preset_colors_4[i]

    # Test applying presets with > 5 layers

    for i in range(4):
        imviz_helper.load_data(arr, data_label=f"array_{i+4}")

    po.layer = "array_5"
    po.image_visible = False
    po.layer = "array_3"

    po.apply_RGB_presets()

    assert po.layer.selected == "array_3"
    assert po.stretch_function.value == "arcsinh"
    po.layer = "array_5"
    # Make sure this one didn't change
    assert po.stretch_function.value == "linear"

    # Turn layer 5 back on
    po.image_visible = True
    po.apply_RGB_presets()

    colorbar_colors = matplotlib.colormaps['gist_rainbow'].resampled(8)
    color_ind = 0

    def _rgb_to_hex(rgb):
        rgb = [int(x * 255) for x in rgb]
        return f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}{rgb[3]:02x}"

    for i in range(8):
        po.layer = f"array_{i}"
        assert po.stretch_function.value == "arcsinh"
        assert po.stretch_preset.value == 99
        assert po.image_color.value == matplotlib.colors.to_hex(colorbar_colors(7-color_ind),
                                                                keep_alpha=True)
        color_ind += 1


def test_track_mixed_states(imviz_helper):
    # Initialize two viewer with 3 data each.
    # Each layer of the data will be RGB
    arr = np.arange(36).reshape(6, 6)
    po = imviz_helper.app.get_tray_item_from_name("g-plot-options")
    rgb_colors = ["#ff0000", "#00ff00", "#0000ff"]

    for i in range(3):
        imviz_helper.load_data(arr, data_label=f"array_{i}")

    po.image_color_mode_value = 'One color per layer'
    for i in range(3):
        po.layer_selected = f"array_{i}"
        po.image_color.value = rgb_colors[i]

    imviz_helper.create_image_viewer(viewer_name="imviz-1")
    po.viewer_selected = "imviz-1"
    po.image_color_mode_value = 'One color per layer'
    for i in range(3):
        imviz_helper.app.add_data_to_viewer("imviz-1", data_label=f"array_{i}")
        po.layer_selected = f"array_{i}"
        po.image_color.value = rgb_colors[i]

    # Switch to multiselect to test mixing and unmixing of states
    po.viewer_multiselect = True
    po.layer_multiselect = True
    po.viewer_selected = ["imviz-0", "imviz-1"]
    assert po.layer.items[-1]["label"] == "array_2"
    # The corresponding layer in each viewer is the same color,
    # so the state is not mixed.
    assert len(po.layer.items[-1]["colors"]) == 1

    # Change the color of one of the layers in one viewer
    po.viewer_selected = ["imviz-1"]
    po.layer_selected = ["array_2"]
    po.image_color.value = "#595959"
    po.viewer_selected = ["imviz-0", "imviz-1"]
    # The color state is now mixed when two viewers are selected
    assert po.layer.items[-1]["label"] == "array_2"
    assert len(po.layer.items[-1]["colors"]) == 2

    # Now test mixed visibility
    po.viewer_selected = ["imviz-1"]
    po.layer_selected = ["array_1", "array_2"]
    po.image_visible.value = False
    po.viewer_selected = ["imviz-0", "imviz-1"]
    assert po.layer.items[-1]["label"] == "array_2"
    assert po.layer.items[-1]["visible"] == 'mixed'
    assert po.layer.items[-2]["label"] == "array_1"
    assert po.layer.items[-2]["visible"] == 'mixed'

    # Test unmixing visibility
    po.image_visible.unmix_state(True)
    assert po.layer.items[-1]["visible"] is True
    assert po.layer.items[-1]["visible"]
    assert po.layer.items[-2]["visible"] is True
    assert po.layer.items[-2]["visible"]

    # Now test unmixing color
    po.viewer_selected = ["imviz-0", "imviz-1"]
    assert len(po.layer.items[-1]["colors"]) > 1
    assert len(po.layer.items[-2]["colors"]) == 1

    # Make sure that all selected layers are no longer
    # mixed state and are the same color
    po.image_color.unmix_state()
    assert len(po.layer.items[-1]["colors"]) == 1
    assert len(po.layer.items[-2]["colors"]) == 1
    assert po.image_color.value == "#00ff00"
    assert po.layer.items[-1]["colors"][0] == "#00ff00"
    assert po.layer.items[-2]["colors"][0] == "#00ff00"

    # test spline stretch mixed state
    po.viewer_selected = ["imviz-0"]
    po.layer_selected = ["array_1"]
    po.stretch_function_value = 'spline'
    po.viewer_selected = ["imviz-0", "imviz-1"]
    assert po.stretch_function_sync['mixed']

    po.vue_unmix_state(['stretch_function', 'stretch_params'])
    assert not po.stretch_function_sync['mixed']
    assert po.stretch_function_value == 'spline'
    assert not po.stretch_params_sync['mixed']


def test_segmentation_image(imviz_helper):
    # Make one circular segment for a hypothetical
    # image with one source:
    nx = ny = 100
    radius = 15
    x0 = y0 = 50

    segmentation_map = np.zeros((nx, ny))
    xx, yy = np.meshgrid(np.arange(nx), np.arange(ny))
    in_circle = np.hypot(xx - x0, yy - y0) < radius
    segmentation_map[in_circle] = 1

    imviz_helper.load_data(segmentation_map)

    plot_opts = imviz_helper.plugins['Plot Options']
    plot_opts.image_colormap = 'Random'

    # ensure that stretch preset is adjusted when the image segmentaiton
    # option is selected for the "Random" colormap, so that all colors
    # are uniquely displayed:
    plot_opts._obj.image_segmentation_map_presets()
    assert plot_opts.stretch_preset.value == 100
    assert plot_opts.stretch_function.value == 'linear'
    assert plot_opts.image_bias.value == 0.5
    assert plot_opts.image_contrast.value == 1.0


def test_imviz_select_all_layers(imviz_helper):
    """
    Test to catch a (fixed) bug that was revealed when trying to select
    all layers when data is float32. This was caused when trying to set
    `stretch_vmin_value`.
    """

    arr = np.arange(36.).reshape(6, 6).astype(np.float32)

    # load three images in one viewer
    with imviz_helper.batch_load():
        for i in range(3):
            imviz_helper.load_data(arr, data_label=f"data_{i}")

    plot_options = imviz_helper.plugins['Plot Options']

    plot_options.layer.multiselect = True
    plot_options.select_all()

    # all layers selected, set stretch function to log for all
    plot_options.stretch_function = 'log'

    # and make sure each layer picked up this change
    for layer in plot_options.image_colormap.linked_states:
        assert layer.as_dict()['stretch'] == 'log'
