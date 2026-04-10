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
    assert result.meta.get('exception', '') == ''
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

    # input is non-text file with no file extension
    binfile = tmp_path / 'data.bin'
    binfile.write_bytes(b'\x00\x01\x80\xff' * 256)
    parser = AstropyTableParser(deconfigged_helper._app, str(binfile))
    assert parser.is_text_file is False
    assert parser.input_ext_format is None


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
    assert expected_substr in result.meta['exception']
