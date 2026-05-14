from astropy.table import Table

from jdaviz.core.loaders.importers.catalog.catalog import CatalogImporter


def test_catalog_importer_is_valid(deconfigged_helper):
    """Test _check_is_valid for CatalogImporter: success and failure cases."""
    resolver = deconfigged_helper.loaders['object']._obj

    def _create_importer(input_data=None):
        return CatalogImporter(app=deconfigged_helper._app,
                               resolver=resolver, parser=None,
                               input=input_data)

    # Success: non-empty table
    importer = _create_importer(input_data=Table({'ra': [10.0, 20.0], 'dec': [-5.0, 10.0]}))
    assert importer._check_is_valid() == ''

    # Failure: non-table input
    importer = _create_importer(input_data='not_a_catalog')
    assert importer._check_is_valid() == 'Input is not a valid catalog.'

    # Failure: empty table
    importer = _create_importer(input_data=Table())
    assert importer._check_is_valid() == 'Input is not a valid catalog.'
