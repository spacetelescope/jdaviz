import pytest
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
