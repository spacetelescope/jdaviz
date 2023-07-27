import pytest
from numpy import allclose
from numpy.testing import assert_allclose

from jdaviz.core.marks import HistogramMark


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

    flux_cube_sample = po.stretch_histogram.marks[0].sample

    # changing viewer should change results
    po.viewer.selected = 'uncert-viewer'
    assert not allclose(po.stretch_histogram.marks[0].sample, flux_cube_sample)

    po.viewer.selected = 'flux-viewer'
    assert_allclose(po.stretch_histogram.marks[0].sample, flux_cube_sample)

    # change viewer limits
    fv = cubeviz_helper.app.get_viewer('flux-viewer')
    fv.state.x_max = 0.5 * fv.state.x_max
    # viewer limits should not be affected by default
    assert_allclose(po.stretch_histogram.marks[0].sample, flux_cube_sample)

    # set to listen to viewer limits, the length of the samples will change
    po.stretch_hist_zoom_limits = True
    assert len(po.stretch_histogram.marks[0].sample) != len(flux_cube_sample)

    po.stretch_vmin.value = 0.5
    po.stretch_vmax.value = 1

    v_min_max_marks = [mark for mark in po.stretch_histogram.marks
                       if isinstance(mark, HistogramMark)]
    assert len(v_min_max_marks) == 2
    assert v_min_max_marks[0].x[0] == po.stretch_vmin.value
    assert v_min_max_marks[1].x[0] == po.stretch_vmax.value

    assert po.stretch_histogram.marks[0].bins == 25
    po.set_histogram_nbins(20)
    assert po.stretch_histogram.marks[0].bins == 20

    po.set_histogram_x_limits(x_min=0.25, x_max=2)
    assert po.stretch_histogram.axes[0].scale.min == 0.25
    assert po.stretch_histogram.axes[0].scale.max == 2

    po.set_histogram_y_limits(y_min=1, y_max=2)
    assert po.stretch_histogram.axes[1].scale.min == 1
    assert po.stretch_histogram.axes[1].scale.max == 2

    po._remove_histogram_marks()
    assert len([mark for mark in po.stretch_histogram.marks
                if isinstance(mark, HistogramMark)]) == 0
    po._add_histogram_marks()
    v_min_max_marks2 = [mark for mark in po.stretch_histogram.marks
                        if isinstance(mark, HistogramMark)]
    assert len(v_min_max_marks2) == 2
    assert v_min_max_marks2[0].x[0] == po.stretch_vmin.value
    assert v_min_max_marks2[1].x[0] == po.stretch_vmax.value

    po.stretch_vmin.value = po.stretch_histogram.marks[0].min - 1
    po.stretch_vmax.value = po.stretch_histogram.marks[0].max + 1

    v_min_max_marks3 = [mark for mark in po.stretch_histogram.marks
                        if isinstance(mark, HistogramMark)]
    assert len(v_min_max_marks3) == 0


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
