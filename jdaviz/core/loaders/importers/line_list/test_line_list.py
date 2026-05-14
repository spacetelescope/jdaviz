from unittest.mock import PropertyMock, patch

import astropy.units as u
from astropy.table import QTable

from jdaviz.core.loaders.importers.line_list.line_list import LineListImporter


def test_line_list_importer_is_valid(deconfigged_helper):
    """Test _check_is_valid for LineListImporter: success and failure cases."""

    app = deconfigged_helper._app

    valid_table = QTable({'linename': ['Ha', 'Hb'], 'rest': [6563, 4861] * u.AA})
    importer = LineListImporter(app=app, resolver=None, parser=None, input=valid_table)

    # Failure: Line Lists plugin not available (deconfigged)
    assert importer._check_is_valid() == 'Line Lists plugin not available.'

    # Success: valid QTable with Line Lists plugin available (specviz)
    with patch.object(type(importer), 'has_default_plugin',
                      new_callable=PropertyMock, return_value=True):
        assert importer._check_is_valid() == ''

    # Failure: non-QTable input
    importer._input = 'not_a_table'
    assert importer._check_is_valid() == 'Input must be a QTable.'

    # Failure: missing 'linename' column
    importer._input = QTable({'rest': [5000, 6000] * u.AA})
    assert importer._check_is_valid() == "Input must have a 'linename' column."

    # Failure: missing 'rest' column
    importer._input = QTable({'linename': ['Ha', 'Hb']})
    assert importer._check_is_valid() == "Input must have a 'rest' column."

    # Failure: 'rest' column without units
    importer._input = QTable({'linename': ['Ha', 'Hb'], 'rest': [5000, 6000]})
    assert importer._check_is_valid() == "'rest' column must be an astropy Quantity object."

    # Failure: negative rest values
    importer._input = QTable({'linename': ['Ha', 'Hb'], 'rest': [-5000, 6000] * u.AA})
    assert importer._check_is_valid() == 'All rest values must be positive.'
