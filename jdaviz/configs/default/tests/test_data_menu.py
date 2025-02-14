from astropy.io import fits
import pytest
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
    specviz_helper.plugins['Subset Tools'].import_region(
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
    specviz_helper.app.data_item_remove("test2")
    assert len(dm._obj.layer_items) == 1
    assert dm._obj.dm_layer_selected == [0]
    assert dm.layer.selected == ['test']


def test_data_menu_add_remove_data(imviz_helper):
    for i in range(3):
        imviz_helper.load_data(np.zeros((2, 2)) + i, data_label=f'image_{i}', show_in_viewer=False)

    dm = imviz_helper.viewers['imviz-0']._obj.data_menu
    assert len(dm._obj.layer_items) == 0
    assert len(dm.layer.choices) == 0
    assert len(dm._obj.dataset.choices) == 3

    dm.add_data('image_0')
    assert dm.layer.choices == ['image_0']
    assert len(dm._obj.dataset.choices) == 2

    with pytest.raises(ValueError,
                       match="Data labels \\['dne1', 'dne2'\\] not able to be loaded into 'imviz-0'.  Must be one of: \\['image_1', 'image_2'\\]"):  # noqa
        dm.add_data('dne1', 'dne2')

    dm.add_data('image_1', 'image_2')
    assert len(dm.layer.choices) == 3
    assert len(dm._obj.dataset.choices) == 0

    dm.layer.selected = ['image_0']
    dm.remove_from_viewer()
    assert len(dm.layer.choices) == 2
    assert len(dm._obj.dataset.choices) == 1

    dm.layer.selected = ['image_1']
    dm.remove_from_app()
    assert len(dm.layer.choices) == 1
    assert len(dm._obj.dataset.choices) == 1


def test_data_menu_create_subset(imviz_helper):
    imviz_helper.load_data(np.zeros((2, 2)), data_label='image', show_in_viewer=True)

    dm = imviz_helper.viewers['imviz-0']._obj.data_menu
    assert imviz_helper.app.session.edit_subset_mode.edit_subset == []

    dm.create_subset('circle')
    assert imviz_helper.app.session.edit_subset_mode.edit_subset == []
    assert imviz_helper.viewers['imviz-0']._obj.toolbar.active_tool_id == 'bqplot:truecircle'


def test_data_menu_remove_subset(specviz_helper, spectrum1d):
    # load 2 data entries
    specviz_helper.load_data(spectrum1d, data_label="test")
    new_spec = specviz_helper.get_spectra(apply_slider_redshift=True)["test"]*0.9
    specviz_helper.load_data(new_spec, data_label="test2")

    dm = specviz_helper.viewers['spectrum-viewer']._obj.data_menu
    sp = specviz_helper.plugins['Subset Tools']

    sp.import_region(SpectralRegion(6000 * spectrum1d.spectral_axis.unit,
                                    6100 * spectrum1d.spectral_axis.unit),
                     combination_mode='new')
    sp.import_region(SpectralRegion(6000 * spectrum1d.spectral_axis.unit,
                                    6100 * spectrum1d.spectral_axis.unit),
                     combination_mode='new')

    assert dm.layer.choices == ['Subset 2', 'Subset 1', 'test2', 'test']
    dm.layer.selected = ['Subset 1']
    dm.remove_from_viewer()

    # subset visibility is set to false, but still appears in menu (unlike removing data)
    assert dm.layer.choices == ['Subset 2', 'Subset 1', 'test2', 'test']
    assert dm._obj.layer_items[1]['label'] == 'Subset 1'
    # TODO: sometimes appearing as mixed right now, known bug
    assert dm._obj.layer_items[1]['visible'] is not True

    # selection should not have changed by removing subset from viewer
    assert dm.layer.selected == ['Subset 1']
    dm.remove_from_app()
    # TODO: not quite sure why this isn't passing, seems to
    # work on local tests, so may just be async?
    # assert dm.layer.choices == ['test', 'test2', 'Subset 2']


def test_data_menu_dq_layers(imviz_helper):
    hdu_data = fits.ImageHDU(np.zeros(shape=(2, 2)))
    hdu_data.name = 'SCI'
    hdu_dq = fits.ImageHDU(np.zeros(shape=(2, 2), dtype=np.int32))
    hdu_dq.name = 'DQ'
    data = fits.HDUList([fits.PrimaryHDU(), hdu_data, hdu_dq])

    imviz_helper.load_data(data, data_label="image", ext=('SCI', 'DQ'), show_in_viewer=True)

    dm = imviz_helper.viewers['imviz-0']._obj.data_menu
    assert dm.layer.choices == ['image[DQ,1]', 'image[SCI,1]']
    assert len(dm._obj.visible_layers) == 2

    # turning off image (parent) data-layer should also turn off DQ
    dm.set_layer_visibility('image[SCI,1]', False)
    assert len(dm._obj.visible_layers) == 0

    # turning on image (parent) should leave DQ off
    dm.set_layer_visibility('image[SCI,1]', True)
    assert len(dm._obj.visible_layers) == 1

    # turning on DQ (child, when parent off) should show parent
    dm.set_layer_visibility('image[SCI,1]', False)
    dm.set_layer_visibility('image[DQ,1]', True)
    assert len(dm._obj.visible_layers) == 2


@pytest.mark.xfail(reason="known issue")
def test_data_menu_subset_appearance(specviz_helper, spectrum1d):
    # NOTE: this test is similar to above - the subset is appearing in time IF there
    # are two data entries, but not in this case with just one
    specviz_helper.load_data(spectrum1d, data_label="test")

    dm = specviz_helper.viewers['spectrum-viewer']._obj.data_menu
    sp = specviz_helper.plugins['Subset Tools']

    sp.import_region(SpectralRegion(6000 * spectrum1d.spectral_axis.unit,
                                    6100 * spectrum1d.spectral_axis.unit))

    # AssertionError: assert ['Subset 1', 'test'] == ['test', 'Subset 1']
    assert dm.layer.choices == ['test', 'Subset 1']


def test_data_menu_view_info(specviz_helper, spectrum1d):
    # load 2 data entries
    specviz_helper.load_data(spectrum1d, data_label="test")
    new_spec = specviz_helper.get_spectra(apply_slider_redshift=True)["test"]*0.9
    specviz_helper.load_data(new_spec, data_label="test2")

    dm = specviz_helper.viewers['spectrum-viewer']._obj.data_menu
    mp = specviz_helper.plugins['Metadata']
    sp = specviz_helper.plugins['Subset Tools']

    sp.import_region(SpectralRegion(6000 * spectrum1d.spectral_axis.unit,
                                    6100 * spectrum1d.spectral_axis.unit),
                     combination_mode='new')
    sp.import_region(SpectralRegion(6200 * spectrum1d.spectral_axis.unit,
                                    6300 * spectrum1d.spectral_axis.unit),
                     combination_mode='new')

    assert dm.layer.choices == ['Subset 2', 'Subset 1', 'test2', 'test']

    dm.layer.selected = ["test2"]
    dm.view_info()
    assert mp.dataset.selected == "test2"

    dm.layer.selected = ["Subset 2"]
    dm.view_info()
    assert sp.subset.selected == "Subset 2"

    dm.layer.selected = ["test", "test2"]
    with pytest.raises(ValueError, match="Only one layer can be selected to view info"):
        dm.view_info()
