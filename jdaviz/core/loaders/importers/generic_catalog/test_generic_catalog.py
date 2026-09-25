"""
Basic tests for the Generic Catalog importer.
"""

import os

import numpy as np
import pytest
from astropy.table import QTable, Table

from jdaviz.configs.default.plugins.viewers import _catalog_kind_from_meta


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
    assert 'Spectral Line List Table' not in choices


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
    assert _catalog_kind_from_meta(data.meta) == 'generic'

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
