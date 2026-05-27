
from astropy.table import Table, QTable
from jdaviz.core.loaders.importers.catalog.catalog import CatalogImporter
from jdaviz.utils import in_ra_comps, in_dec_comps
import pytest


def test_coord_column_detection(deconfigged_helper):
    """
    Test automatic detection of RA/Dec columns with various naming
    conventions, and that non-coordinate columns are not misidentified as
    coordinate columns (e.g 'radial' which contains 'ra' but should not be
    identified as 'Ra'). Examine final output for the user: col_ra and col_dec
    attributes of the importer.
    """

    # Variations of 'ra' and 'dec' that should be correctly identified as coordinate columns
    ra_variations = ['rightascension', 'ra', 'radeg',
                     'radegrees', 'rightascensiondegrees', 'rightascensiondeg',
                     'raobj', 'objra', 'sourcera', 'rasource', 'raj2000', 'ra2000',
                     'worldra', 'targra', 'scira']
    dec_variations = ['declination', 'dec', 'decdeg',
                      'decdegrees', 'declinationdegrees', 'declinationdeg',
                      'decobj', 'objdec', 'decsource', 'sourcedec', 'decj2000',
                      'dec2000', 'worlddec', 'targdec', 'scidec']

    variations_to_pass = list(zip(ra_variations, dec_variations))

    for v in variations_to_pass:
        ra, dec = v  # unpack RA and Dec column names
        tab = QTable({ra: [10.0], dec: [-5.0]})

        ldr = deconfigged_helper.loaders['object']
        ldr.object = tab
        ldr.format = 'Catalog'
        importer = ldr.importer

        # make sure the coordinate columns were correctly identified
        assert importer.col_ra == ra
        assert importer.col_dec == dec

    # check that certain strings that contain 'ra' and 'dec' substrings are not
    # misidentified as coordinate columns
    tab = QTable({'radial_velocity': [10.0], 'fluxradius': [5.0], 'decrement': [1.0]})
    ldr = deconfigged_helper.loaders['object']
    ldr.object = tab
    ldr.format = 'Catalog'
    importer = ldr.importer
    # none of the column names in the input table should have been identified as RA or Dec columns,
    # so they should be set as a placeholder value of '---'
    assert importer.col_ra == '---'
    assert importer.col_dec == '---'


@pytest.mark.parametrize("coordinate_name", ['ra', 'dec'])
def test_coord_column(deconfigged_helper,
                      sky_coord_only_source_catalog,
                      coordinate_name):
    """Test internal method _guess_coord_cols for CatalogImporter: success and failure cases."""
    resolver = deconfigged_helper.loaders['object']._obj
    importer = CatalogImporter(app=deconfigged_helper._app,
                               resolver=resolver, parser=None,
                               input=sky_coord_only_source_catalog)

    variations_to_pass = [coordinate_name.upper(), coordinate_name + '_gaia',
                          'source' + coordinate_name, 'world ' + coordinate_name]

    for v in variations_to_pass:
        tab = QTable({v: [10.0]})
        importer._input = tab
        assert importer._guess_coord_cols(coordinate_name)[0] == v
        assert (in_ra_comps(v) or in_dec_comps(v))

    # specifically test 'right ascension' and 'declination'
    tab = QTable({'rightascension_deg': [10.0], 'declination_deg': [-5.0]})
    importer._input = tab
    if coordinate_name == 'ra':
        assert importer._guess_coord_cols(coordinate_name)[0] == 'rightascension_deg'
    elif coordinate_name == 'dec':
        assert importer._guess_coord_cols(coordinate_name)[0] == 'declination_deg'

    # test failures too
    tab = QTable({'fluxradius': [10.0], 'radial_velocity': [5.0], 'decrement': [1.0]})
    importer._input = tab
    assert importer._guess_coord_cols(coordinate_name)[0] == '---'


def test_pixel_column_detection(deconfigged_helper):
    '''Test automatic detection of x/y columns with various naming
    conventions, and that non-pixel-coordinate columns are not misidentified as
    pixel-coordinate columns (e.g 'galaxy' which contains 'x' but should not be
    identified as x pixel-coordinate).'''

    x_variations = ['X', 'xpix', 'xpixel', 'pixel_x', 'x_coord', 'xsource']
    y_variations = ['Y', 'ypix', 'ypixel', 'pixel_y', 'y_coord', 'ysource']

    variations_to_pass = list(zip(x_variations, y_variations))

    for v in variations_to_pass:
        x, y = v  # unpack RA and Dec column names
        tab = QTable({x: [10.0], y: [5.0]})

        ldr = deconfigged_helper.loaders['object']
        ldr.object = tab
        ldr.format = 'Catalog'
        importer = ldr.importer

        # make sure the coordinate columns were correctly identified
        assert importer.col_x == x
        assert importer.col_y == y

    # check that certain strings that contain 'x' and 'y' substrings are not
    # misidentified as pixel coordinate columns
    tab = QTable({'galaxy': [10.0], 'parallax': [5.0], 'velocity': [1.0]})
    ldr = deconfigged_helper.loaders['object']
    ldr.object = tab
    ldr.format = 'Catalog'
    importer = ldr.importer
    # none of the column names in the input table should have been identified as x or y columns,
    # so they should be set as a placeholder value of '---'
    assert importer.col_x == '---'
    assert importer.col_y == '---'


@pytest.mark.parametrize("coordinate_name", ['x', 'y'])
def test_pixel_column(deconfigged_helper,
                      sky_coord_only_source_catalog,
                      coordinate_name):
    """Test internal method _guess_coord_cols for CatalogImporter: success and failure cases."""
    resolver = deconfigged_helper.loaders['object']._obj
    importer = CatalogImporter(app=deconfigged_helper._app,
                               resolver=resolver, parser=None,
                               input=sky_coord_only_source_catalog)

    variations_to_pass = [coordinate_name.upper(), coordinate_name + '_source',
                          'pixel_' + coordinate_name, coordinate_name + 'pix']

    for v in variations_to_pass:
        tab = QTable({v: [10.0]})
        importer._input = tab
        assert importer._guess_coord_cols(coordinate_name)[0] == v

    # test failures too
    tab = QTable({'galaxy': [10.0], 'parallax': [5.0], 'velocity': [1.0]})
    importer._input = tab
    assert importer._guess_coord_cols(coordinate_name)[0] == '---'


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
