import numpy as np
from specutils import SpectralRegion


def test_data_menu_toggles(specviz_helper, spectrum1d):
    # NOTE: this test is adopted from core.tests.test_data_menu.test_data_menu_toggles
    # which should be removed once the old data menu is removed from jdaviz

    # load 2 data entries
    specviz_helper.load_data(spectrum1d, data_label="test")
    new_spec = specviz_helper.get_spectra(apply_slider_redshift=True)["test"]*0.9
    specviz_helper.load_data(new_spec, data_label="test2")

    # check that both are enabled in the data menu
    sv = specviz_helper.viewers['spectrum-viewer']
    dm = sv._obj.data_menu
    assert len(dm._obj.layer_items) == 2
    assert len(dm._obj.visible_layers) == 2

    # disable (hide layer) for second entry
    dm.set_layer_visibility('test2', False)
    assert len(dm._obj.layer_items) == 2
    assert len(dm._obj.visible_layers) == 1

    # add a subset and make sure it appears for the first data entry but not the second
    specviz_helper.plugins['Subset Tools']._obj.import_region(
        SpectralRegion(6000 * spectrum1d.spectral_axis.unit, 6500 * spectrum1d.spectral_axis.unit))

    assert len(dm._obj.layer_items) == 3
    assert len(dm._obj.visible_layers) == 2
    assert len(sv._obj.layers) == 4
    assert sv._obj.layers[2].visible is True   # subset corresponding to first (visible) data entry
    assert sv._obj.layers[3].visible is False  # subset corresponding to second (hidden) data entry

    # enable data layer from menu and subset should also become visible
    dm.toggle_layer_visibility('test2')
    assert np.all([layer.visible for layer in sv._obj.layers])


def test_data_menu_selection(specviz_helper, spectrum1d):
    # load 2 data entries
    specviz_helper.load_data(spectrum1d, data_label="test")
    new_spec = specviz_helper.get_spectra(apply_slider_redshift=True)["test"]*0.9
    specviz_helper.load_data(new_spec, data_label="test2")

    sv = specviz_helper.viewers['spectrum-viewer']
    dm = sv._obj.data_menu

    # no selection by default
    assert len(dm._obj.dm_layer_selected) == 0
    assert len(dm.layer.selected) == 0

    # test layer -> UI sync
    dm.layer.selected = dm.layer.choices[0]
    assert len(dm._obj.dm_layer_selected) == len(dm.layer.selected)

    # test UI -> layer sync
    dm._obj.dm_layer_selected = [0, 1]
    assert len(dm._obj.dm_layer_selected) == len(dm.layer.selected)

    # test that sync remains during layer deletion
    dm._obj.dm_layer_selected = [1]
    assert dm.layer.selected == ['test']
    specviz_helper.app.remove_data_from_viewer("spectrum-viewer", "test2")
    specviz_helper.app.vue_data_item_remove({"item_name": "test2"})
    assert len(dm._obj.layer_items) == 1
    assert dm._obj.dm_layer_selected == [0]
    assert dm.layer.selected == ['test']
