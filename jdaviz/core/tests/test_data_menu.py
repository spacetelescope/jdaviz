import pytest
import numpy as np

from glue.core.roi import XRangeROI
from astropy.utils.data import download_file

from jdaviz.core.data_formats import identify_helper

# URIs to example JWST/HST files on MAST, and their
# corresponding jdaviz helpers:
example_uri_helper = [
     ['mast:HST/product/id4301ouq_drz.fits', 'imviz'],
     ['mast:HST/product/ldq601030_x1dsum.fits', 'specviz'],
     ['mast:HST/product/o4xw01dkq_flt.fits', 'specviz2d'],
     ['mast:JWST/product/jw02072-c1003_s00002_nirspec_clear-prism-s200a1_x1d.fits',
      'specviz'],
     ['mast:JWST/product/jw01324-o006_s00005_nirspec_f100lp-g140h_s2d.fits',
      'specviz2d'],
     ['mast:JWST/product/jw01345-o001_t021_nircam_clear-f200w_i2d.fits', 'imviz'],
     ['mast:JWST/product/jw01373-o028_t001_nirspec_g395h-f290lp_s3d.fits',
      'cubeviz'],
     ['mast:JWST/product/jw01373-o031_t007_miri_ch1-shortmediumlong_s3d.fits',
      'cubeviz'],
     ['mast:JWST/product/jw01783-o004_t008_nircam_clear-f444w_i2d.fits', 'imviz'],
     ['mast:JWST/product/jw02732-o004_t004_miri_ch1-shortmediumlong_x1d.fits',
      'specviz']
]


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
    app.get_viewer("spectrum-viewer").apply_roi(XRangeROI(6000, 6500))

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


@pytest.mark.skip(reason="filenames changed")
@pytest.mark.remote_data
@pytest.mark.filterwarnings(r"ignore::astropy.wcs.wcs.FITSFixedWarning")
@pytest.mark.parametrize(
    "uri, expected_helper", example_uri_helper
)
def test_auto_config_detection(uri, expected_helper):
    url = f'https://mast.stsci.edu/api/v0.1/Download/file/?uri={uri}'
    fn = download_file(url, timeout=100)
    helper_name, hdul = identify_helper(fn)
    hdul.close()
    assert helper_name == expected_helper
