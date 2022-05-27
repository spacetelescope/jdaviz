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

    for viewer_name in ['mask-viewer', 'spectrum-viewer']:
        assert cubeviz_helper.app.get_viewer(viewer_name).state.show_axes is True

    assert po.show_axes.sync['mixed'] is False

    # adding another viewer should show a mixed-state
    po.viewer.selected = ['flux-viewer', 'uncert-viewer', 'mask-viewer', 'spectrum-viewer']
    # spectrum viewer is excluded from the show_axes logic
    assert len(po.show_axes.linked_states) == 3
    assert len(po.show_axes.sync['icons']) == 3
    assert po.show_axes.sync['mixed'] is True

    # from API could call po.show_axes.unmix_state, but we'll also test the vue-level wrapper
    po.vue_unmix_state('show_axes')
    assert po.show_axes.sync['mixed'] is False
    assert po.show_axes.value is False

    for viewer_name in ['flux-viewer', 'uncert-viewer', 'mask-viewer']:
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
