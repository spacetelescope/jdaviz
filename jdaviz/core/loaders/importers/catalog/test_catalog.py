
from astropy.table import Table
from jdaviz.core.loaders.importers.catalog.catalog import CatalogImporter
from jdaviz.utils import in_ra_comps, in_dec_comps
import pytest


@pytest.mark.parametrize("coordinate_name", ['ra', 'dec'])
def test_coord_column(deconfigged_helper,
                      sky_coord_only_source_catalog,
                      coordinate_name):

    resolver = deconfigged_helper.loaders['object']._obj
    importer = CatalogImporter(app=deconfigged_helper._app,
                               resolver=resolver, parser=None,
                               input=sky_coord_only_source_catalog)

    variations_to_pass = [coordinate_name.upper(), coordinate_name + '_gaia',
                          'source' + coordinate_name, 'world ' + coordinate_name]

    for v in variations_to_pass:
        this_table = sky_coord_only_source_catalog.copy()
        this_table.rename_column(coordinate_name, v)
        importer._input = this_table
        assert importer._guess_coord_cols(coordinate_name)[0] == v
        if coordinate_name == 'ra':
            assert in_ra_comps(v)
        elif coordinate_name == 'dec':
            assert in_dec_comps(v)

    variations_to_fail = ['fluxradius', 'radial_velocity', 'decrement']
    for v in variations_to_fail:
        this_table = sky_coord_only_source_catalog.copy()
        this_table.rename_column(coordinate_name, v)
        importer._input = this_table
        assert importer._guess_coord_cols(coordinate_name)[0] == '---'
        if coordinate_name == 'ra':
            assert not in_ra_comps(v)
        elif coordinate_name == 'dec':
            assert not in_dec_comps(v)

    # specifically test that 'right ascension' is read as an RA column and not as a Dec column
    this_table = sky_coord_only_source_catalog.copy()
    this_table.rename_column(coordinate_name, 'right ascension')
    importer._input = this_table
    if coordinate_name == 'ra':
        assert importer._guess_coord_cols(coordinate_name)[0] == 'right ascension'
    elif coordinate_name == 'dec':
        assert importer._guess_coord_cols(coordinate_name)[0] == '---'


@pytest.mark.parametrize("pixel_name", ['x', 'y'])
def test_pixel_column(deconfigged_helper,
                      sky_coord_only_source_catalog,
                      pixel_name):

    resolver = deconfigged_helper.loaders['object']._obj
    importer = CatalogImporter(app=deconfigged_helper._app,
                               resolver=resolver, parser=None,
                               input=sky_coord_only_source_catalog)

    sky_coord_only_source_catalog.rename_column('ra', 'x')
    sky_coord_only_source_catalog.rename_column('dec', 'y')

    variations_to_check = {(pixel_name.upper(), pixel_name.upper()),
                           (pixel_name + 'source', pixel_name + 'source'),
                           (pixel_name + '_pix', pixel_name + '_pix'),
                           ('pix_' + pixel_name, 'pix_' + pixel_name),
                           ('galaxy', '---')
                           }

    for v in variations_to_check:
        this_table = sky_coord_only_source_catalog.copy()
        this_table.rename_column(pixel_name, v[0])
        importer._input = this_table
        assert importer._guess_coord_cols(pixel_name)[0] == v[1]


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
