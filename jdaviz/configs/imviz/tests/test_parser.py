import pytest
from unittest.mock import MagicMock, patch
from astropy import units as u
from astropy.io import fits

from jdaviz.configs.imviz.helper import split_filename_with_fits_ext
from jdaviz.configs.imviz.plugins.parsers import (
    HAS_JWST_ASDF, _validate_image2d, _validate_bunit, _parse_image)

test_hook = MagicMock()


@pytest.mark.parametrize(
    ('filename', 'ans'),
    [('/path/to/cache/contents', ['/path/to/cache/contents', None, 'contents']),
     ('file://path/image.fits[SCI]', ['file://path/image.fits', 'SCI', 'image']),
     ('image.fits[dq,2]', ['image.fits', ('dq', 2), 'image']),
     ('/path/to/image.fits', ['/path/to/image.fits', None, 'image']),
     ('../image.fits.gz[1]', ['../image.fits.gz', 1, 'image.fits'])])
def test_filename_split(filename, ans):
    filepath, ext, data_label = split_filename_with_fits_ext(filename)
    assert filepath == ans[0]
    if ans[1] is None:
        assert ext is None
    else:
        assert ext == ans[1]
    assert data_label == ans[2]


def test_validate_image2d():
    # Not 2D image
    hdu = fits.ImageHDU([0, 0])
    assert not _validate_image2d(hdu, raise_error=False)
    with pytest.raises(ValueError, match='Imviz cannot load this HDU'):
        _validate_image2d(hdu)

    # 2D Image
    hdu = fits.ImageHDU([[0, 0], [0, 0]])
    assert _validate_image2d(hdu)


def test_validate_bunit():
    with pytest.raises(u.UnitsError):
        _validate_bunit('NOT_A_UNIT')

    assert not _validate_bunit('Mjy-sr', raise_error=False)  # Close but not quite
    assert _validate_bunit('MJy/sr')


# TODO: Write real tests
class TestParseImage:
    def setup_method(self, method):
        test_hook.resetmock()

    def teardown_method(self, method):
        pass

    def test_no_data_label(self):
        with pytest.raises(NotImplementedError, match='should be set'):
            _parse_image(None, None, None, False)

    @pytest.mark.skipif(not HAS_JWST_ASDF, reason='jwst not installed')
    @pytest.mark.remote_data
    def test_parse_jwst_nircam_level2(self):
        url = 'https://data.science.stsci.edu/redirect/JWST/jwst-data_analysis_tools/stellar_photometry/jw01072001001_01101_00001_nrcb1_cal.fits'  # noqa: E501

    @pytest.mark.remote_data
    def test_parse_hst_drz(self):
        url = 'https://mast.stsci.edu/api/v0.1/Download/file?bundle_name=MAST_2021-04-21T1828.sh&uri=mast:HST/product/jclj01010_drz.fits'  # noqa: E501
