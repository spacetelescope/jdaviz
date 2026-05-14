from astropy.table import Table

from jdaviz.core.loaders.importers.catalog.catalog import CatalogImporter


def test_catalog_importer_is_valid(deconfigged_helper):
    """Test all string-returning scenarios in CatalogImporter._check_is_valid."""
    resolver = deconfigged_helper.loaders['object']._obj

    # Non-table, non-HDUList input
    importer = CatalogImporter(app=deconfigged_helper._app,
                               resolver=resolver, parser=None,
                               input='not_a_catalog')
    assert importer._check_is_valid() == 'Input is not a valid catalog.'

    # Empty table
    importer = CatalogImporter(app=deconfigged_helper._app,
                               resolver=resolver, parser=None,
                               input=Table())
    assert importer._check_is_valid() == 'Input is not a valid catalog.'
