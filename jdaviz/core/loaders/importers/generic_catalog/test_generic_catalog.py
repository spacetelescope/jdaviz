"""
Basic tests for the Generic Catalog importer.
"""

import os

import numpy as np
import pytest
from astropy.io import fits
from astropy.table import QTable, Table


def _make_generic_table():
    """Table with no source-position or spectral-line columns."""
    return Table({'col1': ['A', 'B', 'C'],
                  'col2': [1, 2, 3],
                  'col3': [True, False, True]})


def test_generic_catalog_format_available(deconfigged_helper):
    ldr = deconfigged_helper.loaders['object']
    ldr.object = _make_generic_table()
    assert 'Generic Catalog' in ldr.format.choices


def test_generic_catalog_supported_viewers(deconfigged_helper):
    ldr = deconfigged_helper.loaders['object']
    ldr.object = _make_generic_table()
    ldr.format = 'Generic Catalog'

    choices = ldr.importer.viewer.create_new.choices
    for viewer in ('Scatter', 'Histogram', 'Table'):
        assert viewer in choices
    assert 'Source Catalog Table' not in choices
    assert 'Spectral Line Table' not in choices


def test_generic_catalog_col_other_choices(deconfigged_helper):
    """All input columns are offered, and none are selected by default."""
    ldr = deconfigged_helper.loaders['object']
    ldr.object = _make_generic_table()
    ldr.format = 'Generic Catalog'

    assert ldr.importer.col_other.choices == ['col1', 'col2', 'col3']
    assert ldr.importer.col_other.selected == []


@pytest.mark.parametrize('from_file', [True, False])
def test_load_generic_catalog(deconfigged_helper, tmp_path, from_file):
    table = _make_generic_table()
    if from_file:
        fn = os.path.join(tmp_path, 'generic.ecsv')
        table.write(fn)
        inp = fn
    else:
        inp = table

    deconfigged_helper.load(inp, format='Generic Catalog', data_label='generic',
                            col_other=['col1', 'col2', 'col3'])

    dc = deconfigged_helper._app.data_collection
    assert len(dc) == 1
    data = dc['generic']

    # classified as a generic table, not a source catalog or line list
    assert data.meta['_importer'] == 'GenericCatalogImporter'

    qtab = data.get_object(QTable)
    assert set(qtab.colnames) == {'ID', 'col1', 'col2', 'col3'}
    assert len(qtab) == len(table)
    for col in ('col1', 'col2', 'col3'):
        assert np.all(qtab[col] == table[col])

    # an index 'ID' column is added when the input has none
    assert np.all(qtab['ID'] == np.arange(len(table)))
    assert data.meta['_jdaviz_loader_id_col'] == 'ID'


def test_load_generic_catalog_column_subset(deconfigged_helper):
    """Only the selected columns (plus the added ID) are loaded."""
    deconfigged_helper.load(_make_generic_table(), format='Generic Catalog',
                            data_label='generic', col_other=['col2'])

    qtab = deconfigged_helper._app.data_collection['generic'].get_object(QTable)
    assert set(qtab.colnames) == {'ID', 'col2'}


def test_load_generic_catalog_existing_id_column(deconfigged_helper):
    """An existing 'ID' column is kept as-is rather than replaced by an index."""
    table = _make_generic_table()
    table['ID'] = ['x', 'y', 'z']

    deconfigged_helper.load(table, format='Generic Catalog', data_label='generic',
                            col_other=['ID', 'col1'])

    qtab = deconfigged_helper._app.data_collection['generic'].get_object(QTable)
    assert set(qtab.colnames) == {'ID', 'col1'}
    assert list(qtab['ID']) == ['x', 'y', 'z']


def test_load_generic_catalog_into_table_viewer(deconfigged_helper):
    ldr = deconfigged_helper.loaders['object']
    ldr.object = _make_generic_table()
    ldr.format = 'Generic Catalog'
    ldr.importer.col_other = ['col1', 'col2', 'col3']
    ldr.importer.viewer.create_new = 'Table'
    ldr.load()

    assert 'Table' in deconfigged_helper.viewers
    loaded = deconfigged_helper.viewers['Table'].data_menu.data_labels_loaded
    assert len(loaded) == 1


def test_generic_catalog_empty_table_invalid(deconfigged_helper):
    ldr = deconfigged_helper.loaders['object']
    with pytest.raises(ValueError, match='empty'):
        ldr.object = Table()
    assert 'Generic Catalog' not in ldr.format.choices


def test_load_generic_catalog_from_hdulist(deconfigged_helper):
    """
    Test loading a catalog from a FITS HDUList containing a single
    BinTableHDU extension via the Generic Catalog importer.
    """
    table = _make_generic_table()
    primary_hdu = fits.PrimaryHDU()
    table_hdu = fits.BinTableHDU(table, name='CATALOG')
    hdulist = fits.HDUList([primary_hdu, table_hdu])

    ldr = deconfigged_helper.loaders['object']
    ldr.object = hdulist

    assert ldr.format == 'Generic Catalog'

    # Primary HDU should be filtered out of the extension choices
    extension_labels = ldr.importer.extension.choices
    assert len(extension_labels) == 1
    assert extension_labels[0] == '1: [CATALOG,1]'

    ldr.importer.col_other = ['col1', 'col2', 'col3']
    ldr.importer.viewer.create_new = 'Table'
    ldr.load()

    dc = deconfigged_helper._app.data_collection
    assert len(dc) == 1
    qtab = dc[0].get_object(QTable)
    assert set(qtab.colnames) == {'ID', 'col1', 'col2', 'col3'}
    assert len(qtab) == len(table)


def test_hdulist_multiple_table_extensions_generic_catalog(deconfigged_helper):
    """
    Test loading a catalog from an HDUList with multiple table extensions
    with different column names, and verify that the 'additional columns'
    dropdown updates correctly when switching between extensions.
    """
    table1 = Table({'colA': [1, 2], 'colB': ['x', 'y']})
    table2 = Table({'colC': [3, 4], 'colD': ['z', 'w']})

    hdulist = fits.HDUList([fits.PrimaryHDU(),
                            fits.BinTableHDU(table1, name='T1'),
                            fits.BinTableHDU(table2, name='T2')])

    ldr = deconfigged_helper.loaders['object']
    ldr.object = hdulist
    assert ldr.format == 'Generic Catalog'

    extension_labels = ldr.importer.extension.choices
    assert len(extension_labels) == 2
    assert extension_labels[0] == '1: [T1,1]'
    assert extension_labels[1] == '2: [T2,1]'

    # first extension selected by default
    assert ldr.importer.extension.selected == ['1: [T1,1]']
    col_other_labels = [item['label'] for item in ldr.importer.col_other.items]
    assert 'colA' in col_other_labels
    assert 'colC' not in col_other_labels

    # switch to second extension, dropdown should update to its columns
    ldr.importer.extension.selected = ['2: [T2,1]']
    col_other_labels = [item['label'] for item in ldr.importer.col_other.items]
    assert 'colC' in col_other_labels
    assert 'colA' not in col_other_labels

    # selecting no extension should not raise an error
    ldr.importer.extension.selected = []


def test_load_generic_catalog_from_fits_multiselect(deconfigged_helper):
    """
    Test loading multiple catalogs from a multi-extension FITS file at once
    using multiselect mode.
    """
    table1 = Table({'col1': [1, 2], 'col2': ['a', 'b']})
    table2 = Table({'col1': [3, 4], 'col2': ['c', 'd']})

    hdul = fits.HDUList([fits.PrimaryHDU(), fits.BinTableHDU(table1),
                         fits.BinTableHDU(table2)])

    ldr = deconfigged_helper.loaders['object']
    ldr.object = hdul
    assert ldr.format == 'Generic Catalog'

    assert ldr.importer.extension.multiselect is True

    ldr.importer.extension.selected = ldr.importer.extension.choices

    # these two tables share common column names, so no warning expected
    assert ldr.importer._obj.no_common_col_msg == ''

    ldr.importer.col_other = ['col1', 'col2']
    ldr.importer()

    dc = deconfigged_helper._app.data_collection
    assert len(dc) == 1
    qtab = dc[0].get_object(QTable)
    assert len(qtab) == len(table1) + len(table2)
    assert list(qtab['col1']) == list(table1['col1']) + list(table2['col1'])
    assert list(qtab['col2']) == list(table1['col2']) + list(table2['col2'])

    # now test tables that don't share any common column names
    table3 = Table({'col3': [5, 6], 'col4': ['e', 'f']})
    hdul2 = fits.HDUList([fits.PrimaryHDU(), fits.BinTableHDU(table1),
                          fits.BinTableHDU(table3)])

    ldr.object = hdul2
    assert ldr.format == 'Generic Catalog'

    ldr.importer.extension.selected = ldr.importer.extension.choices

    assert ldr.importer.col_other.choices == ['---']

    msg = (
        "The selected extensions have no columns in common. "
        "Please select a single extension to load, or select "
        "multiple extensions that have at least one column "
        "name in common to enable loading in multiselect mode."
    )
    assert ldr.importer._obj.no_common_col_msg == msg
