import astropy.units as u
from astropy.io import fits
from astropy.table import QTable, Table
from astropy.tests.helper import assert_quantity_allclose
import pytest

from jdaviz.core.loaders.importers.spectral_lines.spectral_lines import SpectralLinesImporter


@pytest.fixture(autouse=True)
def enable_spectral_lines_dev_flag(deconfigged_helper):
    """Exercise spectral-line importer behavior with the feature enabled."""
    deconfigged_helper._app.state.dev_spectral_lines = True


def test_spectral_lines_importer_is_valid(deconfigged_helper):
    """Test _check_is_valid for SpectralLinesImporter: success and failure cases."""
    app = deconfigged_helper._app

    valid_table = QTable({'wavelength': [6562.8, 4861.3] * u.AA,
                          'name': ['Ha', 'Hb']})

    importer = SpectralLinesImporter(app=app, resolver=None, parser=None,
                                     input=valid_table)
    assert importer.is_valid
    assert importer._check_is_valid() == ''

    # non-table input (a string) should not be valid
    importer._input = 'not_a_table'
    assert importer._check_is_valid() == 'Input must be an astropy Table or QTable.'

    # an empty table should not be valid
    importer._input = QTable({'wavelength': [] * u.AA})
    assert importer._check_is_valid() == 'Input table is empty.'

    # a regular astropy Table (not QTable) should be accepted
    importer._input = Table({'wavelength': [6562.8], 'name': ['Ha']})
    assert importer._check_is_valid() == ''


@pytest.mark.parametrize('col_name', [
    'wavelength', 'Wavelength', 'WAVELENGTH',
    'wave', 'Wav', 'wl', 'lambda', 'lam',
    'restwave', 'rest_wave', 'frequency', 'FREQ', 'nu', 'rest-freq', 'rest freq'
])
def test_wavelength_column_detection(deconfigged_helper, col_name):
    """
    Wavelength and frequency-like column names should be automatically detected for
    'spectral_loc'. Added some variation in capitalization / spacing to ensure
    flexibility.
    """
    ldr = deconfigged_helper.loaders['object']
    ldr.object = QTable({col_name: [6562.8, 4861.3], 'flux': [1.0, 0.5]})
    assert ldr.format == 'Spectral Lines'
    importer = ldr.importer
    assert importer.spectral_loc == col_name

    # load into a Table viewer and verify the data appears there
    importer.viewer.create_new = 'Spectral Line Table'
    importer()

    tv = deconfigged_helper.viewers['Spectral Line Table']
    assert len(tv._obj.glue_viewer.layers) == 1


def test_spectral_unit_column_detection(deconfigged_helper):
    """
    Columns from a Q table that already have spectral units should be detected,
    even if the column name doesn't indicate that it is a frequency or
    wavelength column.
    """
    ldr = deconfigged_helper.loaders['object']
    ldr.object = QTable({'pos': [6562.8, 4861.3] * u.AA, 'name': ['Ha', 'Hb']})
    assert ldr.format == 'Spectral Lines'
    importer = ldr.importer
    assert importer.spectral_loc == 'pos'


def test_spectral_loc_excludes_non_numeric_columns(deconfigged_helper):
    """
    Non-numeric columns should be filtered out of spectral_loc choices,
    otherwise an error is raised when they are cast to a float.
    """
    ldr = deconfigged_helper.loaders['object']
    ldr.object = QTable({'wavelength': [6562.8, 4861.3],
                         'name': ['Ha', 'Hb'],       # string – not numeric
                         'flag': [True, False]})      # bool – not float-castable via astype
    assert ldr.format == 'Spectral Lines'
    importer = ldr.importer

    choices = importer.spectral_loc.choices
    assert 'wavelength' in choices
    assert '---' in choices
    assert 'name' not in choices


def test_no_spectral_column_detected(deconfigged_helper):
    """Without a spectral column, Spectral Lines is not valid and Generic Catalog is used."""
    ldr = deconfigged_helper.loaders['object']
    ldr.object = QTable({'flux': [1.0, 0.5], 'name': ['Ha', 'Hb']})
    assert 'Spectral Lines' not in ldr.format.choices
    assert ldr.format == 'Generic Catalog'


def test_spectral_loc_has_unit_true(deconfigged_helper):
    """spectral_loc_has_unit should be True when column has recognised spectral units."""
    app = deconfigged_helper._app
    table = QTable({'wavelength': [6562.8, 4861.3] * u.AA})
    importer = SpectralLinesImporter(app=app, resolver=None, parser=None, input=table)

    importer.spectral_loc_selected = 'wavelength'
    assert importer.spectral_loc_has_unit is True


def test_spectral_loc_has_unit_false(deconfigged_helper):
    """spectral_loc_has_unit should be False when column has no units."""
    app = deconfigged_helper._app
    table = QTable({'wavelength': [6562.8, 4861.3]})  # no units
    importer = SpectralLinesImporter(app=app, resolver=None, parser=None, input=table)

    importer.spectral_loc_selected = 'wavelength'
    assert importer.spectral_loc_has_unit is False


def test_spectral_loc_no_selection_disables_import(deconfigged_helper):
    """Selecting '---' should set import_disabled_msg."""
    app = deconfigged_helper._app
    table = QTable({'wavelength': [6562.8] * u.AA})
    importer = SpectralLinesImporter(app=app, resolver=None, parser=None, input=table)

    importer.spectral_loc_selected = '---'
    assert importer.import_disabled_msg != ''


def test_output_with_units_already_present(deconfigged_helper):
    """When the spectral column has units, they should pass through unchanged."""
    app = deconfigged_helper._app
    table = QTable({'wavelength': [6562.8, 4861.3] * u.AA, 'name': ['Ha', 'Hb']})
    importer = SpectralLinesImporter(app=app, resolver=None, parser=None, input=table)
    importer.spectral_loc_selected = 'wavelength'

    out = importer.output
    assert isinstance(out, QTable)
    assert 'wavelength' in out.colnames
    assert out['wavelength'].unit == u.AA
    assert out.meta['_jdaviz_loader_spectral_loc_col'] == 'wavelength'


def test_output_unit_applied_when_missing(deconfigged_helper):
    """When the spectral column has no units, the chosen unit should be applied."""
    app = deconfigged_helper._app
    table = QTable({'wavelength': [6562.8, 4861.3]})
    importer = SpectralLinesImporter(app=app, resolver=None, parser=None, input=table)
    importer.spectral_loc_selected = 'wavelength'
    importer.spectral_loc_unit_selected = 'nm'

    out = importer.output
    assert out['wavelength'].unit == u.nm


def test_output_additional_columns(deconfigged_helper):
    """Selected additional columns should appear in the output."""
    app = deconfigged_helper._app
    table = QTable({'wavelength': [6562.8] * u.AA, 'flux': [1.0], 'name': ['Ha']})
    importer = SpectralLinesImporter(app=app, resolver=None, parser=None, input=table)
    importer.spectral_loc_selected = 'wavelength'
    importer.col_other_selected = ['flux', 'name']

    out = importer.output
    assert 'flux' in out.colnames
    assert 'name' in out.colnames


def test_supported_viewers():
    """
    TODO:_get_supported_viewers should include Scatter, Spectral Line Table
    and Histogram viewers? currently only the Spectral Line Table is supported."""
    viewers = SpectralLinesImporter._get_supported_viewers()
    assert len(viewers) == 1  # only table viewer for now
    references = [v['reference'] for v in viewers]
    assert 'spectral-line-table-viewer' in references


def test_load_spectral_lines_from_hdulist(deconfigged_helper):
    """
    Test loading a spectral line table from a FITS HDUList containing a single
    BinTableHDU extension via the Spectral Lines importer.
    """
    table = QTable({'wavelength': [6562.8, 4861.3] * u.AA, 'name': ['Ha', 'Hb']})
    primary_hdu = fits.PrimaryHDU()
    table_hdu = fits.BinTableHDU(table, name='LINES')
    hdulist = fits.HDUList([primary_hdu, table_hdu])

    ldr = deconfigged_helper.loaders['object']
    ldr.object = hdulist

    assert ldr.format == 'Spectral Lines'

    # Primary HDU should be filtered out of the extension choices
    extension_labels = ldr.importer.extension.choices
    assert len(extension_labels) == 1
    assert extension_labels[0] == '1: [LINES,1]'

    assert ldr.importer.spectral_loc == 'wavelength'

    ldr.importer.viewer.create_new = 'Spectral Line Table'
    ldr.load()

    dc = deconfigged_helper._app.data_collection
    assert len(dc) == 1
    tv = deconfigged_helper.viewers['Spectral Line Table']
    assert len(tv._obj.glue_viewer.layers) == 1


def test_hdulist_multiple_table_extensions_spectral_lines(deconfigged_helper):
    """
    Test loading a spectral line table from an HDUList with multiple table
    extensions with different column names, and verify that the spectral
    location/line name column dropdowns update correctly when switching
    between extensions.
    """
    table1 = QTable({'wave1': [6562.8, 4861.3] * u.AA, 'name1': ['Ha', 'Hb']})
    table2 = QTable({'wave2': [1.2, 2.3] * u.um, 'name2': ['X', 'Y']})

    hdulist = fits.HDUList([fits.PrimaryHDU(),
                            fits.BinTableHDU(table1, name='LINES1'),
                            fits.BinTableHDU(table2, name='LINES2')])

    ldr = deconfigged_helper.loaders['object']
    ldr.object = hdulist
    assert ldr.format == 'Spectral Lines'

    extension_labels = ldr.importer.extension.choices
    assert len(extension_labels) == 2
    assert extension_labels[0] == '1: [LINES1,1]'
    assert extension_labels[1] == '2: [LINES2,1]'

    # first extension selected by default, spectral_loc guessed from its units
    assert ldr.importer.extension.selected == ['1: [LINES1,1]']
    assert ldr.importer.spectral_loc == 'wave1'

    spectral_loc_labels = [item['label'] for item in ldr.importer.spectral_loc.items]
    assert 'wave1' in spectral_loc_labels
    assert 'wave2' not in spectral_loc_labels

    # switch to second extension, dropdowns should update to its columns
    ldr.importer.extension.selected = ['2: [LINES2,1]']
    assert ldr.importer.spectral_loc == 'wave2'

    spectral_loc_labels = [item['label'] for item in ldr.importer.spectral_loc.items]
    assert 'wave2' in spectral_loc_labels
    assert 'wave1' not in spectral_loc_labels

    col_other_labels = [item['label'] for item in ldr.importer.col_other.items]
    assert 'name2' in col_other_labels
    assert 'name1' not in col_other_labels

    # selecting no extension should not raise an error
    ldr.importer.extension.selected = []


def test_load_spectral_lines_from_fits_multiselect(deconfigged_helper):
    """
    Test loading multiple spectral line tables from a multi-extension FITS
    file at once using multiselect mode.
    """
    table1 = QTable({'wavelength': [6562.8, 4861.3] * u.AA, 'name': ['Ha', 'Hb']})
    table2 = QTable({'wavelength': [5000.0, 5500.0] * u.AA, 'name': ['X', 'Y']})

    hdul = fits.HDUList([fits.PrimaryHDU(), fits.BinTableHDU(table1),
                         fits.BinTableHDU(table2)])

    ldr = deconfigged_helper.loaders['object']
    ldr.object = hdul
    assert ldr.format == 'Spectral Lines'

    assert ldr.importer.extension.multiselect is True

    ldr.importer.extension.selected = ldr.importer.extension.choices

    # these two tables share common column names, so no warning expected
    assert ldr.importer._obj.no_common_col_msg == ''
    assert ldr.importer.spectral_loc == 'wavelength'

    ldr.importer.col_other = ['name']
    ldr.importer()

    dc = deconfigged_helper._app.data_collection
    assert len(dc) == 1
    qtab = dc[0].get_object(QTable)
    assert len(qtab) == len(table1) + len(table2)
    assert_quantity_allclose(qtab['wavelength'][:len(table1)], table1['wavelength'])
    assert_quantity_allclose(qtab['wavelength'][len(table1):], table2['wavelength'])
    assert list(qtab['name']) == list(table1['name']) + list(table2['name'])

    # now test tables that don't share any common column names
    table3 = QTable({'wave2': [1.0, 2.0] * u.AA, 'label': ['A', 'B']})
    hdul2 = fits.HDUList([fits.PrimaryHDU(), fits.BinTableHDU(table1),
                          fits.BinTableHDU(table3)])

    ldr.object = hdul2
    assert ldr.format == 'Spectral Lines'

    ldr.importer.extension.selected = ldr.importer.extension.choices

    assert ldr.importer.spectral_loc.choices == ['---']
    assert ldr.importer.col_other.choices == ['---']

    msg = (
        "The selected extensions have no columns in common. "
        "Please select a single extension to load, or select "
        "multiple extensions that have at least one column "
        "name in common to enable loading in multiselect mode."
    )
    assert ldr.importer._obj.no_common_col_msg == msg
