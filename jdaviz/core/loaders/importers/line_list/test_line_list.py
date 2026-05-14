import astropy.units as u
from astropy.table import QTable

from jdaviz.core.loaders.importers.line_list.line_list import LineListImporter


def test_line_list_importer_is_valid(deconfigged_helper):
    """Test all string-returning scenarios in LineListImporter._check_is_valid."""
    app = deconfigged_helper._app

    def _create_importer(input_data=None):
        return LineListImporter(app=app, resolver=None, parser=None, input=input_data)

    # Non-QTable input
    importer = _create_importer(input_data='not_a_table')
    assert importer._check_is_valid() == 'Input must be a QTable.'

    # Missing 'linename' column
    importer = _create_importer(input_data=QTable({'rest': [5000, 6000] * u.AA}))
    assert importer._check_is_valid() == "Input must have a 'linename' column."

    # Missing 'rest' column
    importer = _create_importer(input_data=QTable({'linename': ['Ha', 'Hb']}))
    assert importer._check_is_valid() == "Input must have a 'rest' column."

    # 'rest' column without units
    importer = _create_importer(input_data=QTable({'linename': ['Ha', 'Hb'],
                                                  'rest': [5000, 6000]}))
    assert importer._check_is_valid() == "'rest' column must be an astropy Quantity object."

    # Negative rest values
    importer = _create_importer(input_data=QTable({'linename': ['Ha', 'Hb'],
                                                   'rest': [-5000, 6000] * u.AA}))
    assert importer._check_is_valid() == 'All rest values must be positive.'

    # Line Lists plugin not available
    importer = _create_importer(input_data=QTable({'linename': ['Ha', 'Hb'],
                                                   'rest': [5000, 6000] * u.AA}))
    assert importer._check_is_valid() == 'Line Lists plugin not available.'
