import pytest
from numpy import allclose
from numpy.testing import assert_allclose


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

    hist_mark = po.stretch_histogram.marks['histogram']
    flux_cube_sample = hist_mark.sample

    # changing viewer should change results
    po.viewer.selected = 'uncert-viewer'
    assert not allclose(hist_mark.sample, flux_cube_sample)

    po.viewer.selected = 'flux-viewer'
    assert_allclose(hist_mark.sample, flux_cube_sample)

    # change viewer limits
    fv = cubeviz_helper.app.get_viewer('flux-viewer')
    fv.state.x_max = 0.5 * fv.state.x_max
    # viewer limits should not be affected by default
    assert_allclose(hist_mark.sample, flux_cube_sample)

    # set to listen to viewer limits, the length of the samples will change
    po.stretch_hist_zoom_limits = True
    assert len(hist_mark.sample) != len(flux_cube_sample)

    po.stretch_vmin.value = 0.5
    po.stretch_vmax.value = 1

    assert po.stretch_histogram.marks['vmin'].x[0] == po.stretch_vmin.value
    assert po.stretch_histogram.marks['vmax'].x[0] == po.stretch_vmax.value

    assert hist_mark.bins == 25
    po.stretch_hist_nbins = 20
    assert hist_mark.bins == 20

    po.set_histogram_x_limits(x_min=0.25, x_max=2)
    assert po.stretch_histogram.figure.axes[0].scale.min == 0.25
    assert po.stretch_histogram.figure.axes[0].scale.max == 2

    po.set_histogram_y_limits(y_min=1, y_max=2)
    assert po.stretch_histogram.figure.axes[1].scale.min == 1
    assert po.stretch_histogram.figure.axes[1].scale.max == 2

    po.stretch_vmin.value = hist_mark.min - 1
    po.stretch_vmax.value = hist_mark.max + 1

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
