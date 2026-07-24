import astropy.units as u
from astropy.table import QTable, Table
import pytest

from jdaviz.core.loaders.importers.spectral_lines.spectral_lines import SpectralLinesImporter


def test_spectral_lines_importer_is_valid(deconfigged_helper):
    """Test _check_is_valid for SpectralLinesImporter: success and failure cases."""
    app = deconfigged_helper._app

    valid_table = QTable({'wavelength': [6562.8, 4861.3] * u.AA,
                          'name': ['Ha', 'Hb']})

    importer = SpectralLinesImporter(app=app, resolver=None, parser=None,
                                     input=valid_table)
    assert importer.is_valid
    assert importer._check_is_valid() == ''

    # non table input (a string) should not be valid
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
    ldr.format = 'Spectral Lines'
    importer = ldr.importer
    assert importer.spectral_loc == col_name


def test_spectral_unit_column_detection(deconfigged_helper):
    """
    Columns from a Q table that already have spectral units should be detected,
    even if the column name doesn't indicate that it is a frequency or
    wavelength column.
    """
    ldr = deconfigged_helper.loaders['object']
    ldr.object = QTable({'pos': [6562.8, 4861.3] * u.AA, 'name': ['Ha', 'Hb']})
    ldr.format = 'Spectral Lines'
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
    ldr.format = 'Spectral Lines'
    importer = ldr.importer

    choices = importer.spectral_loc.choices
    assert 'wavelength' in choices
    assert '---' in choices
    assert 'name' not in choices


def test_no_spectral_column_detected(deconfigged_helper):
    """When no spectral column is found, selection should default to '---'."""
    ldr = deconfigged_helper.loaders['object']
    ldr.object = QTable({'flux': [1.0, 0.5], 'name': ['Ha', 'Hb']})
    ldr.format = 'Spectral Lines'
    importer = ldr.importer
    assert importer.spectral_loc == '---'


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
    importer.medium_selected = 'Vacuum'

    out = importer.output
    assert isinstance(out, QTable)
    assert 'wavelength' in out.colnames
    assert out['wavelength'].unit == u.AA
    assert out.meta['_jdaviz_loader_spectral_loc_col'] == 'wavelength'
    assert out.meta['_jdaviz_loader_medium'] == 'Vacuum'


def test_output_unit_applied_when_missing(deconfigged_helper):
    """When the spectral column has no units, the chosen unit should be applied."""
    app = deconfigged_helper._app
    table = QTable({'wavelength': [6562.8, 4861.3]})
    importer = SpectralLinesImporter(app=app, resolver=None, parser=None, input=table)
    importer.spectral_loc_selected = 'wavelength'
    importer.spectral_loc_unit_selected = 'nm'
    importer.medium_selected = 'Air'

    out = importer.output
    assert out['wavelength'].unit == u.nm
    assert out.meta['_jdaviz_loader_medium'] == 'Air'


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
    """_get_supported_viewers should include Scatter, Table and Histogram viewers."""
    viewers = SpectralLinesImporter._get_supported_viewers()
    assert len(viewers) == 3
    references = [v['reference'] for v in viewers]
    assert 'scatter-viewer' in references
    assert 'table-viewer' in references
    assert 'histogram-viewer' in references
