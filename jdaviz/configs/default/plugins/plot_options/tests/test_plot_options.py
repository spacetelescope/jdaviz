import pytest


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
    # from API could call po.show_axes.value = False, but we'll also test the vue-level wrapper
    po.vue_set_value({'name': 'show_axes_value', 'value': False})
    assert po.show_axes.value is False

    for viewer_name in ['flux-viewer', 'uncert-viewer']:
        assert cubeviz_helper.app.get_viewer(viewer_name).state.show_axes is False

    assert cubeviz_helper.app.get_viewer('spectrum-viewer').state.show_axes is True

    assert po.show_axes.sync['mixed'] is False

    # adding another viewer should show a mixed-state
    po.viewer.selected = ['flux-viewer', 'uncert-viewer', 'spectrum-viewer']
    # spectrum viewer is excluded from the show_axes logic
    assert len(po.show_axes.linked_states) == 2
    assert len(po.show_axes.sync['icons']) == 2
    assert po.show_axes.sync['mixed'] is False

    # from API could call po.show_axes.unmix_state, but we'll also test the vue-level wrapper
    po.vue_unmix_state('show_axes')
    assert po.show_axes.sync['mixed'] is False
    assert po.show_axes.value is False

    for viewer_name in ['flux-viewer', 'uncert-viewer']:
        assert cubeviz_helper.app.get_viewer(viewer_name).state.show_axes is False

    for viewer_name in ['spectrum-viewer']:
        assert cubeviz_helper.app.get_viewer(viewer_name).state.show_axes is True

    po.multiselect = False
    # should default back to the first selected entry
    assert po.viewer.multiselect is False
    assert po.viewer.selected == 'flux-viewer'
    assert po.show_axes.value is False

    po.viewer.selected = 'spectrum-viewer'
    assert po.show_axes.sync['in_subscribed_states'] is False
    assert len(po.show_axes.linked_states) == 0


@pytest.mark.filterwarnings('ignore')
def test_user_api(cubeviz_helper, spectrum1d_cube):
    cubeviz_helper.load_data(spectrum1d_cube)
    po = cubeviz_helper.plugins['Plot Options']

    assert po.multiselect is False
    assert "multiselect" in po.viewer.__repr__()

    po.select_all()
    assert po.multiselect is True
    assert len(po.viewer.selected) == 4

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
    assert hasattr(po.stretch_perc, 'choices')
    assert len(po.stretch_perc.choices) > 1
    assert "choices" in po.stretch_perc.__repr__()
    assert not hasattr(po.bitmap_contrast, 'choices')
    assert "choices" not in po.bitmap_contrast.__repr__()

    # try setting with both label and value
    po.stretch_perc = 90
    po.stretch_perc = 'Min/Max'
