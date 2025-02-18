import pytest
import numpy as np

from astropy.utils.data import download_file
from specutils import SpectralRegion

from jdaviz.core.data_formats import identify_helper


def test_data_menu_toggles(specviz_helper, spectrum1d):
    # load 2 data entries
    specviz_helper.load_data(spectrum1d, data_label="test")
    app = specviz_helper.app
    sv = app.get_viewer('spectrum-viewer')
    new_spec = specviz_helper.get_spectra(apply_slider_redshift=True)["test"]*0.9
    specviz_helper.load_data(new_spec, data_label="test2")

    # check that both are enabled in the data menu
    selected_data_items = app._viewer_item_by_id('specviz-0')['selected_data_items']
    data_ids = list(selected_data_items.keys())
    assert len(data_ids) == 2
    assert np.all([visible == 'visible' for visible in selected_data_items.values()])
    assert len(sv.layers) == 2
    assert np.all([layer.visible for layer in sv.layers])

    # disable (hide layer) for second entry
    app.set_data_visibility('specviz-0', app._get_data_item_by_id(data_ids[-1])['name'],
                            visible=False)

    selected_data_items = app._viewer_item_by_id('specviz-0')['selected_data_items']
    assert selected_data_items[data_ids[0]] == 'visible'
    assert sv.layers[0].visible is True
    assert selected_data_items[data_ids[1]] == 'hidden'
    assert sv.layers[1].visible is False

    # add a subset and make sure it appears for the first data entry but not the second
    specviz_helper.plugins['Subset Tools'].import_region(
        SpectralRegion(6000 * spectrum1d.spectral_axis.unit, 6500 * spectrum1d.spectral_axis.unit))

    assert len(sv.layers) == 4
    assert sv.layers[2].visible is True   # subset corresponding to first (visible) data entry
    assert sv.layers[3].visible is False  # subset corresponding to second (hidden) data entry

    # enable data layer from menu and subset should also become visible
    app.set_data_visibility('specviz-0', app._get_data_item_by_id(data_ids[-1])['name'],
                            visible=True)
    assert np.all([layer.visible for layer in sv.layers])

    # manually hide just the data layer, and the visiblity state in the menu should show as mixed
    sv.layers[3].visible = False

    selected_data_items = app._viewer_item_by_id('specviz-0')['selected_data_items']
    assert selected_data_items[data_ids[0]] == 'visible'
    assert selected_data_items[data_ids[1]] == 'mixed'


def test_visibility_toggle(imviz_helper):
    arr = np.arange(4).reshape((2, 2))
    imviz_helper.load_data(arr, data_label='no_results_data')
    app = imviz_helper.app
    iv = app.get_viewer('imviz-0')

    # regression test for https://github.com/spacetelescope/jdaviz/issues/1723
    # test to make sure plot options (including percentile) stick when toggling visibility
    # via the data menu checkboxes
    selected_data_items = app._viewer_item_by_id('imviz-0')['selected_data_items']
    data_ids = list(selected_data_items.keys())
    assert selected_data_items[data_ids[0]] == 'visible'
    assert iv.layers[0].visible is True
    po = imviz_helper.plugins['Plot Options']
    po.stretch_preset = 90
    assert po.stretch_preset.value == 90

    app.set_data_visibility('imviz-0', app._get_data_item_by_id(data_ids[0])['name'],
                            visible=False)

    assert iv.layers[0].visible is False

    app.set_data_visibility('imviz-0', app._get_data_item_by_id(data_ids[0])['name'],
                            visible=True)
    assert iv.layers[0].visible is True
    assert po.stretch_preset.value == 90


# URIs to example JWST/HST files on MAST, and their corresponding jdaviz helpers.
@pytest.mark.remote_data
@pytest.mark.filterwarnings(r"ignore::astropy.wcs.wcs.FITSFixedWarning")
@pytest.mark.parametrize(("uri, expected_helper"), [
    ('mast:HST/product/jclj01010_drz.fits', 'imviz'),
    ('mast:JWST/product/jw02732-o004_t004_miri_ch1-shortmediumlong_x1d.fits', 'specviz'),
    ('mast:jwst/product/jw01538-o161_s000000001_nirspec_f290lp-g395h-s1600a1_s2d.fits', 'specviz2d'),  # noqa: E501
    ('mast:JWST/product/jw02727-o002_t062_nircam_clear-f277w_i2d.fits', 'imviz'),
    ('mast:JWST/product/jw02732-o004_t004_miri_ch1-shortmediumlong_s3d.fits', 'cubeviz')])
def test_auto_config_detection(uri, expected_helper):
    url = f'https://mast.stsci.edu/api/v0.1/Download/file/?uri={uri}'
    fn = download_file(url, timeout=100)
    helper_name, hdul = identify_helper(fn)
    hdul.close()
    assert helper_name == expected_helper
