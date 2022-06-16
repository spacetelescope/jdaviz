import numpy as np

from glue.core.roi import XRangeROI


def test_data_menu_toggles(specviz_helper, spectrum1d):
    # load 2 data entries
    specviz_helper.load_spectrum(spectrum1d, data_label="test")
    app = specviz_helper.app
    sv = app.get_viewer('spectrum-viewer')
    new_spec = specviz_helper.get_spectra(apply_slider_redshift=True)["test"]*0.9
    specviz_helper.load_spectrum(new_spec, data_label="test2")

    # check that both are enabled in the data menu
    selected_data_items = app._viewer_item_by_id('specviz-0')['selected_data_items']
    data_ids = list(selected_data_items.keys())
    assert len(data_ids) == 2
    assert np.all([visible == 'visible' for visible in selected_data_items.values()])
    assert len(sv.layers) == 2
    assert np.all([layer.visible for layer in sv.layers])

    # disable (hide layer) for second entry
    app.vue_data_item_visibility({'id': 'specviz-0',
                                  'item_id': data_ids[-1],
                                  'visible': False})

    selected_data_items = app._viewer_item_by_id('specviz-0')['selected_data_items']
    assert selected_data_items[data_ids[0]] == 'visible'
    assert sv.layers[0].visible is True
    assert selected_data_items[data_ids[1]] == 'hidden'
    assert sv.layers[1].visible is False

    # add a subset and make sure it appears for the first data entry but not the second
    app.get_viewer("spectrum-viewer").apply_roi(XRangeROI(6000, 6500))

    assert len(sv.layers) == 4
    assert sv.layers[2].visible is True   # subset corresponding to first (visible) data entry
    assert sv.layers[3].visible is False  # subset corresponding to second (hidden) data entry

    # enable data layer from menu and subset should also become visible
    app.vue_data_item_visibility({'id': 'specviz-0',
                                  'item_id': data_ids[-1],
                                  'visible': True})
    assert np.all([layer.visible for layer in sv.layers])

    # manually hide just the data layer, and the visiblity state in the menu should show as mixed
    sv.layers[3].visible = False

    selected_data_items = app._viewer_item_by_id('specviz-0')['selected_data_items']
    assert selected_data_items[data_ids[0]] == 'visible'
    assert selected_data_items[data_ids[1]] == 'mixed'
