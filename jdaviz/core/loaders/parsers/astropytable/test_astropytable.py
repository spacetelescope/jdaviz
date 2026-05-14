from astropy.table import QTable
import astropy.units as u
import pytest

from jdaviz.core.loaders.parsers.astropytable import AstropyTableParser


@pytest.mark.parametrize(
    ('file_ext', 'write_format', 'expected_format'), [
        pytest.param('.ecsv', 'ascii.ecsv', 'ascii.ecsv', id='ecsv'),
        pytest.param('.csv', 'ascii.csv', 'ascii.csv', id='csv'),
        pytest.param('.vot', 'votable', None, id='votable'),
        pytest.param('.dat', 'ascii.csv', None, id='dat'),
        pytest.param('', 'ascii.csv', 'ascii', id='no_ext'),
    ])
def test_valid_table_files(deconfigged_helper, tmp_path,
                           file_ext, write_format,
                           expected_format):
    """
    Write a table to disk in various formats / extensions and
    verify that the parser resolves the format correctly and
    produces a valid output table.
    """
    t = QTable()
    t['ra'] = [10.0, 20.0, 30.0] * u.deg
    t['dec'] = [-5.0, 10.0, 25.0] * u.deg
    t['flux'] = [1.1, 2.2, 3.3] * u.Jy

    filepath = str(tmp_path / f'catalog{file_ext}')
    t.write(filepath, format=write_format, overwrite=True)

    parser = AstropyTableParser(deconfigged_helper._app, filepath)

    assert parser.input_ext_format == expected_format

    result = parser.output
    assert result.meta.get('_jdaviz_exception', '') == ''
    assert 'ra' in result.colnames
    assert 'dec' in result.colnames
    assert 'flux' in result.colnames
    assert len(result) == 3


def test_format_edge_cases(deconfigged_helper, tmp_path):
    """
    Test both ``is_text_file`` and ``input_ext_format``
    for edge cases.
    """
    # input is QTable object, not a file
    t = QTable({'a': [1, 2]})
    parser = AstropyTableParser(deconfigged_helper._app, t)
    assert parser.is_text_file is False
    assert parser.input_ext_format is None

    # input is non-text file with file extension
    binfile = tmp_path / 'data.bin'
    binfile.write_bytes(b'\x00\x01\x80\xff' * 256)
    parser = AstropyTableParser(deconfigged_helper._app, str(binfile))
    assert parser.is_text_file is False
    assert parser.input_ext_format is None

    # input is non-text file with no file extension
    binfile = tmp_path / 'data'
    binfile.write_bytes(b'\x00\x01\x80\xff' * 256)
    parser = AstropyTableParser(deconfigged_helper._app, str(binfile))
    assert parser.is_text_file is False
    with pytest.raises(ValueError):
        _ = parser.input_ext_format


@pytest.mark.parametrize(
    ('content', 'fmt', 'expected_substr'), [
        pytest.param('', 'ascii.csv', 'Table is empty', id='empty_file'),
        pytest.param('a,b,c\n', 'ascii.csv', 'Table is empty', id='no_rows'),
    ])
def test_try_qtable_read_failures(deconfigged_helper, tmp_path, content, fmt,
                                  expected_substr):
    """
    ``_try_qtable_read`` must populate ``meta['exception']``
    when the read fails, i.e. no rows.
    """
    f = tmp_path / 'bad.csv'
    f.write_text(content)
    parser = AstropyTableParser(deconfigged_helper._app, str(f))
    result = parser._try_qtable_read(fmt)
    assert expected_substr in result.meta['_jdaviz_exception']


def test_astropytable_parser_is_valid(deconfigged_helper, tmp_path):
    """Test _check_is_valid for AstropyTableParser: success and failure cases."""
    import numpy as np
    from astropy.io import fits

    # Success: non-empty QTable object
    parser = AstropyTableParser(deconfigged_helper._app,
                                QTable({'a': [1, 2], 'b': [3, 4]}))
    assert parser._check_is_valid() == ''

    # Success: non-empty table read from an ECSV file
    filepath = str(tmp_path / 'catalog.ecsv')
    QTable({'ra': [10.0] * u.deg, 'dec': [-5.0] * u.deg}).write(
        filepath, format='ascii.ecsv', overwrite=True)
    parser = AstropyTableParser(deconfigged_helper._app, filepath)
    assert parser._check_is_valid() == ''

    # Failure: None input
    parser = AstropyTableParser(deconfigged_helper._app, None)
    assert parser._check_is_valid() == 'Input must not be None.'

    # Failure: empty QTable and empty table from file
    parser = AstropyTableParser(deconfigged_helper._app, QTable())
    assert parser._check_is_valid() == 'Table is empty.'

    filepath = str(tmp_path / 'empty.ecsv')
    QTable({'a': u.Quantity([], unit=u.m)}).write(filepath, format='ascii.ecsv',
                                                 overwrite=True)
    parser = AstropyTableParser(deconfigged_helper._app, filepath)
    assert parser._check_is_valid() == 'Table is empty.'

    # Failure: FITS HDU and HDUList rejected
    for inp in (fits.PrimaryHDU(), fits.HDUList([fits.PrimaryHDU()])):
        parser = AstropyTableParser(deconfigged_helper._app, inp)
        assert parser._check_is_valid() == 'Input is a FITS HDU, not a table.'

    # Failure: numpy array rejected
    parser = AstropyTableParser(deconfigged_helper._app, np.array([1, 2, 3]))
    assert parser._check_is_valid() == 'Input is a numpy array, not a table.'

    # Failure: FITS file on disk rejected
    filepath = str(tmp_path / 'test.fits')
    fits.PrimaryHDU(data=[1, 2, 3]).writeto(filepath)
    parser = AstropyTableParser(deconfigged_helper._app, filepath)
    assert parser._check_is_valid() == 'Input is a FITS file, not a table.'
