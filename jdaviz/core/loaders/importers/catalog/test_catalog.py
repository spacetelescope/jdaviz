
from astropy.table import Table
import pytest

from jdaviz.core.loaders.importers.catalog.catalog import CatalogImporter


def test_catalog_importer_is_valid(deconfigged_helper):
    """Test _check_is_valid for CatalogImporter: success and failure cases."""
    resolver = deconfigged_helper.loaders['object']._obj

    # Success: non-empty table
    importer = CatalogImporter(app=deconfigged_helper._app,
                               resolver=resolver, parser=None,
                               input=Table({'ra': [10.0, 20.0], 'dec': [-5.0, 10.0]}))
    assert importer._check_is_valid() == ''

    # Failure: non-table input
    importer._input = 'not_a_catalog'
    assert importer._check_is_valid() == 'Input is not a valid catalog.'

    # Failure: empty table
    importer._input = Table()
    assert importer._check_is_valid() == 'Input is not a valid catalog.'
