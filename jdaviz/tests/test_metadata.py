import pytest
from astropy.io import fits

from jdaviz.utils import standardize_metadata, COMMENTCARD_KEY


def test_metadata_plain_dict():
    metadata = {'a': 1, 'b': 2, 'c': {'d': 42}}
    out_meta = standardize_metadata(metadata)
    assert out_meta == metadata

    # Make sure input is unchanged.
    del out_meta['c']
    assert out_meta == {'a': 1, 'b': 2}
    assert 'c' in metadata


def test_metadata_nested_fits_header():
    hdu = fits.PrimaryHDU()
    metadata = {'a': 1, 'header': hdu.header}
    out_meta = standardize_metadata(metadata)
    assert 'header' not in out_meta
    assert sorted(out_meta.keys()) == ['BITPIX', 'EXTEND', 'NAXIS', 'SIMPLE', COMMENTCARD_KEY, 'a']
    assert out_meta[COMMENTCARD_KEY]['BITPIX'] == 'array data type'
    assert 'BITPIX' in out_meta[COMMENTCARD_KEY]._header
    assert 'a' not in out_meta[COMMENTCARD_KEY]._header

    # Make sure input is unchanged.
    assert 'header' in metadata


def test_metadata_fits_header():
    hdu = fits.PrimaryHDU()
    out_meta = standardize_metadata(hdu.header)
    assert sorted(out_meta.keys()) == ['BITPIX', 'EXTEND', 'NAXIS', 'SIMPLE', COMMENTCARD_KEY]
    assert out_meta[COMMENTCARD_KEY]['BITPIX'] == 'array data type'
    assert 'BITPIX' in out_meta[COMMENTCARD_KEY]._header

    # Make sure input is unchanged.
    del out_meta['BITPIX']
    assert 'BITPIX' in hdu.header

    # Make sure you can still nest it afterwards if you want.
    # Similar logic is used to separate primary header in Metadata Viewer plugin.
    hdu_2 = fits.ImageHDU()
    out_meta['image_meta'] = standardize_metadata(hdu_2.header)
    assert out_meta['image_meta']['XTENSION'] == 'IMAGE'


def test_metadata_invalid():
    with pytest.raises(TypeError, match='metadata must be dictionary or FITS header'):
        standardize_metadata([1, 2, 3])
