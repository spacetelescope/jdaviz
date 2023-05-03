import numpy as np
import pytest
from astropy.io import fits
from astropy.nddata import NDData

from jdaviz.configs.default.plugins.metadata_viewer.metadata_viewer import MetadataViewer


def test_view_dict(imviz_helper):
    mv = MetadataViewer(app=imviz_helper.app)
    arr = np.zeros((2, 2), dtype=np.float32)
    ndd_1 = NDData(arr, meta={
        'EXTNAME': 'SCI', 'EXTVER': 1, 'BAR': 10.0, '_hidden': 'no show',
        'HISTORY': 'Hmm', '': 'Invalid', 'FOO': '', 'COMMENT': 'a test', 'BOZO': None})
    ndd_2 = NDData(arr, meta={
        'EXTNAME': 'ASDF', 'REF': {'bar': 10.0, 'foo': {'1': '', '2': [1, 2]}}})

    # MEF
    ndd_3 = fits.HDUList([fits.PrimaryHDU(), fits.ImageHDU(arr)])
    ndd_3[1].name = 'DATA'
    ndd_4 = fits.HDUList([fits.PrimaryHDU(), fits.ImageHDU(arr)])
    ndd_4[0].header['APERTURE'] = ('#TODO', 'Aperture')
    ndd_4[1].name = 'DATA'

    imviz_helper.load_data(ndd_1, data_label='has_simple_meta')
    imviz_helper.load_data(ndd_2, data_label='has_nested_meta')
    imviz_helper.load_data(ndd_3, data_label='has_primary')
    imviz_helper.load_data(ndd_4, data_label='has_primary_2')
    imviz_helper.load_data(arr, data_label='no_meta')
    assert mv.dataset.labels == ['has_simple_meta[DATA]', 'has_nested_meta[DATA]',
                                 'has_primary[DATA,1]', 'has_primary_2[DATA,1]', 'no_meta']

    mv.dataset_selected = 'has_simple_meta[DATA]'
    assert not mv.has_primary
    assert not mv.show_primary
    assert not mv.has_comments
    assert mv.has_metadata
    assert mv.metadata == [
        ('BAR', '10.0', ''), ('BOZO', 'None', ''), ('EXTNAME', 'SCI', ''),
        ('EXTVER', '1', ''), ('FOO', '', ''), ('WCS-ONLY', 'False', '')]

    mv.dataset_selected = 'has_nested_meta[DATA]'
    assert not mv.has_primary
    assert not mv.show_primary
    assert not mv.has_comments
    assert mv.has_metadata
    assert mv.metadata == [
        ('EXTNAME', 'ASDF', ''), ('REF.bar', '10.0', ''),
        ('REF.foo.1', '', ''), ('REF.foo.2.0', '1', ''), ('REF.foo.2.1', '2', ''),
        ('WCS-ONLY', 'False', '')
    ]

    mv.dataset_selected = 'has_primary[DATA,1]'
    assert mv.has_primary
    assert not mv.show_primary
    assert mv.has_comments
    assert mv.has_metadata
    assert mv.metadata == [('BITPIX', '-32', 'array data type'),
                           ('EXTNAME', 'DATA', 'extension name'),
                           ('GCOUNT', '1', 'number of groups'),
                           ('NAXIS', '2', 'number of array dimensions'),
                           ('NAXIS1', '2', ''), ('NAXIS2', '2', ''),
                           ('PCOUNT', '0', 'number of parameters'),
                           ('XTENSION', 'IMAGE', 'Image extension')]
    mv.show_primary = True
    assert mv.metadata == [('BITPIX', '8', 'array data type'), ('EXTEND', 'True', ''),
                           ('NAXIS', '0', 'number of array dimensions'),
                           ('SIMPLE', 'True', 'conforms to FITS standard')]

    mv.dataset_selected = 'has_primary_2[DATA,1]'
    assert mv.show_primary  # Make sure it sticks if possible
    assert mv.has_comments
    assert mv.metadata == [('APERTURE', '#TODO', 'Aperture'),
                           ('BITPIX', '8', 'array data type'), ('EXTEND', 'True', ''),
                           ('NAXIS', '0', 'number of array dimensions'),
                           ('SIMPLE', 'True', 'conforms to FITS standard')]

    mv.dataset_selected = 'no_meta'
    assert not mv.has_primary
    assert not mv.show_primary
    assert not mv.has_comments
    assert not mv.has_metadata
    assert mv.metadata == []


def test_view_invalid(imviz_helper):
    mv = MetadataViewer(app=imviz_helper.app)
    assert mv.dataset.labels == []

    # Should not even happen but if it does, do not crash.
    with pytest.raises(ValueError):
        mv.dataset_selected = 'foo'
    assert mv.dataset_selected == ''
    assert not mv.has_primary
    assert not mv.show_primary
    assert not mv.has_comments
    assert not mv.has_metadata
    assert mv.metadata == []
