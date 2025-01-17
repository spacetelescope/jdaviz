import os

import pytest
from astropy.wcs import FITSFixedWarning

from jdaviz.utils import alpha_index, download_uri_to_path


@pytest.mark.parametrize("test_input,expected", [(0, 'a'), (1, 'b'), (25, 'z'), (26, 'aa'),
                                                 (701, 'zz'), (702, '{a')])
def test_alpha_index(test_input, expected):
    assert alpha_index(test_input) == expected


def test_alpha_index_exceptions():
    with pytest.raises(TypeError, match="index must be an integer"):
        alpha_index(4.2)
    with pytest.raises(ValueError, match="index must be positive"):
        alpha_index(-1)


def test_uri_to_download_bad_scheme(imviz_helper):
    uri = "file://path/to/file.fits"
    with pytest.raises(ValueError, match=r'URI file://path/to/file\.fits with scheme file'):
        imviz_helper.load_data(uri)


@pytest.mark.remote_data
def test_uri_to_download_nonexistent_mast_file(imviz_helper):
    # this validates as a mast uri but doesn't actually exist on mast:
    uri = "mast:JWST/product/jw00000-no-file-here.fits"
    with pytest.raises(ValueError, match='Failed query for URI'):
        imviz_helper.load_data(uri, cache=False)


@pytest.mark.remote_data
def test_url_to_download_imviz_local_path_warning(imviz_helper):
    url = "https://www.astropy.org/astropy-data/tutorials/FITS-images/HorseHead.fits"
    match_local_path_msg = (
        'You requested to cache data to the .*local_path.*supported for downloads of '
        'MAST URIs.*astropy download cache instead.*'
    )
    with (
        pytest.warns(FITSFixedWarning, match="'datfix' made the change"),
        pytest.warns(UserWarning, match=match_local_path_msg)
    ):
        imviz_helper.load_data(url, cache=True, local_path='horsehead.fits')


def test_uri_to_download_specviz_local_path_check():
    uri = "mast:JWST/product/jw02732-o004_t004_miri_ch1-shortmediumlong_x1d.fits"
    local_path = download_uri_to_path(uri, cache=False, dryrun=True)  # No download

    # Wrong: '.\\JWST/product/jw02732-o004_t004_miri_ch1-shortmediumlong_x1d.fits'
    # Correct:  '.\\jw02732-o004_t004_miri_ch1-shortmediumlong_x1d.fits'
    assert local_path == os.path.join(os.curdir, "jw02732-o004_t004_miri_ch1-shortmediumlong_x1d.fits")  # noqa: E501


@pytest.mark.remote_data
def test_uri_to_download_specviz(specviz_helper, tmp_path):
    uri = "mast:JWST/product/jw02732-o004_t004_miri_ch1-shortmediumlong_x1d.fits"
    local_path = str(tmp_path / uri.split('/')[-1])
    specviz_helper.load_data(uri, cache=True, local_path=local_path)


@pytest.mark.remote_data
def test_uri_to_download_specviz2d(specviz2d_helper, tmp_path):
    uri = "mast:jwst/product/jw01538-o161_s000000001_nirspec_f290lp-g395h-s1600a1_s2d.fits"
    local_path = str(tmp_path / uri.split('/')[-1])
    specviz2d_helper.load_data(uri, cache=True, local_path=local_path)
