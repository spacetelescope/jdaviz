import pytest
from astropy.utils.data import download_file

from jdaviz.core.data_formats import identify_helper


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
    assert len(helper_name) == 1 and helper_name[0] == expected_helper
