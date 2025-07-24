import os
import warnings

import pytest

from jdaviz.utils import alpha_index, download_uri_to_path, get_cloud_fits, cached_uri
from astropy.io import fits


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
    with pytest.raises(ValueError, match="no valid loaders found for input"):
        imviz_helper.load_data(uri)


@pytest.mark.remote_data
def test_uri_to_download_nonexistent_mast_file(imviz_helper):
    # this validates as a mast uri but doesn't actually exist on mast:
    uri = "mast:JWST/product/jw00000-no-file-here.fits"
    with pytest.raises(ValueError, match='Failed query for URI'):
        # NOTE: this test will attempt to reach out to MAST via astroquery
        # even if cache is available.
        imviz_helper.load_data(uri, cache=False)


@pytest.mark.remote_data
def test_url_to_download_imviz_local_path_warning(imviz_helper):
    url = "https://www.astropy.org/astropy-data/tutorials/FITS-images/HorseHead.fits"

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        imviz_helper.load_data(url, cache=True, local_path='horsehead.fits')


def test_uri_to_download_specviz_local_path_check():
    # NOTE: do not use cached_uri here since no download should occur
    uri = "mast:JWST/product/jw02732-c1001_t004_miri_ch1-short_x1d.fits"
    local_path = download_uri_to_path(uri, cache=False, dryrun=True)  # No download

    # Wrong: '.\\JWST/product/jw02732-c1001_t004_miri_ch1-short_x1d.fits'
    # Correct:  '.\\jw02732-c1001_t004_miri_ch1-short_x1d.fits'
    assert local_path == os.path.join(os.curdir, "jw02732-c1001_t004_miri_ch1-short_x1d.fits")  # noqa: E501


@pytest.mark.remote_data
def test_uri_to_download_specviz(specviz_helper):
    uri = cached_uri("mast:JWST/product/jw02732-c1001_t004_miri_ch1-short_x1d.fits")
    specviz_helper.load_data(uri, cache=True)


@pytest.mark.remote_data
def test_uri_to_download_specviz2d(specviz2d_helper):
    uri = cached_uri("mast:jwst/product/jw01538-o161_s000000001_nirspec_f290lp-g395h-s1600a1_s2d.fits")  # noqa: E501
    specviz2d_helper.load_data(uri, cache=True)


@pytest.mark.remote_data
def test_load_s3_fits(imviz_helper):
    """Test loading a JWST FITS file from an S3 URI into Imviz."""
    s3_uri = "s3://stpubdata/jwst/public/jw02727/L3/t/o002/jw02727-o002_t062_nircam_clear-f277w_i2d.fits"  # noqa: E501
    imviz_helper.load_data(s3_uri)
    assert len(imviz_helper.app.data_collection) > 0


@pytest.mark.remote_data
def test_get_cloud_fits_ext():
    s3_uri = "s3://stpubdata/jwst/public/jw02727/L3/t/o002/jw02727-o002_t062_nircam_clear-f277w_i2d.fits"  # noqa: E501
    hdul = get_cloud_fits(s3_uri)
    assert isinstance(hdul, fits.HDUList)

    hdul = get_cloud_fits(s3_uri, ext="SCI")
    assert isinstance(hdul, fits.HDUList)

    hdul = get_cloud_fits(s3_uri, ext=["SCI"])
    assert isinstance(hdul, fits.HDUList)
