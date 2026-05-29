from astropy.coordinates import SkyCoord
from astropy.table import Table, QTable
import astropy.units as u
from jdaviz.core.loaders.importers.catalog.catalog import CatalogImporter
from regions import PixCoord


def test_coord_column_detection(deconfigged_helper):
    """
    Test automatic detection of RA/Dec columns with various naming
    conventions, and that non-coordinate columns are not misidentified as
    coordinate columns (e.g 'radial' which contains 'ra' but should not be
    identified as 'Ra'). Examine final output for the user: col_ra and col_dec
    attributes of the importer.
    """

    # Variations of 'ra' and 'dec' that should be correctly identified as coordinate columns
    # testing a mix of case/delimeter variations
    ra_variations = ['Right_Ascension', 'ra', 'radeg',
                     'radegrees', 'right-ascension-Degrees', 'rightascension_deg',
                     'raobj', 'objra', 'sourcera', 'Rasource', 'raj2000', 'ra2000',
                     'worldra', 'targra', 'sci-ra']
    dec_variations = ['declination', 'dec', 'dec_deg',
                      'dec-degrees', 'declination_degrees', 'declinationdeg',
                      'decobj', 'objdec', 'DECsource', 'sourcedec', 'decJ2000',
                      'dec2000', 'world_dec', 'targdec', 'SCI_dec']

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


def test_skycoord_column_detection(deconfigged_helper):
    """
    Test automatic detection of ra/dec columns when input catalog has a column of SkyCoord objects.
    """
    ra = [149.0, 150.0, 151.0] * u.degree
    dec = [1.9, 2.0, 2.1] * u.degree
    x = [1, 2, 3]
    y = [4, 5, 6]

    # Success: SkyCoord instance
    tab = QTable({'coords': SkyCoord(ra=ra, dec=dec), 'x': x, 'y': y})
    ldr = deconfigged_helper.loaders['object']
    ldr.object = tab
    ldr.format = 'Catalog'
    importer = ldr.importer

    # make sure the coordinate columns were correctly identified
    assert isinstance(importer.input['coords'], SkyCoord)
    assert 'SkyCoord_RA' in importer.output.keys()
    assert 'SkyCoord_Dec' in importer.output.keys()


def test_pixcoord_column_detection(deconfigged_helper):
    """
    If a PixCoord object is passed to the catalog importer, it should ignore those columns.
    """
    ra = [149.0, 150.0, 151.0] * u.degree
    dec = [1.9, 2.0, 2.1] * u.degree
    x = [1, 2, 3]
    y = [4, 5, 6]

    # Failure: PixCoord instance
    tab = QTable({'coords': SkyCoord(ra=ra, dec=dec), 'pix': PixCoord(x=x, y=y)})
    ldr = deconfigged_helper.loaders['object']
    ldr.object = tab
    ldr.format = 'Catalog'
    importer = ldr.importer

    # make sure x and y are ignored
    assert 'pix' not in importer.output.keys()


def test_coord_column_detection(deconfigged_helper):
    """
    Test automatic detection of RA/Dec columns with various naming
    conventions, and that non-coordinate columns are not misidentified as
    coordinate columns (e.g 'radial' which contains 'ra' but should not be
    identified as 'Ra'). Examine final output for the user: col_ra and col_dec
    attributes of the importer.
    """

    # Variations of 'ra' and 'dec' that should be correctly identified as coordinate columns
    # testing a mix of case/delimeter variations
    ra_variations = ['Right_Ascension', 'ra', 'radeg',
                     'radegrees', 'right-ascension-Degrees', 'rightascension_deg',
                     'raobj', 'objra', 'sourcera', 'Rasource', 'raj2000', 'ra2000',
                     'worldra', 'targra', 'sci-ra']
    dec_variations = ['declination', 'dec', 'dec_deg',
                      'dec-degrees', 'declination_degrees', 'declinationdeg',
                      'decobj', 'objdec', 'DECsource', 'sourcedec', 'decJ2000',
                      'dec2000', 'world_dec', 'targdec', 'SCI_dec']

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


def test_skycoord_column_detection(deconfigged_helper):
    """
    Test automatic detection of ra/dec columns when input catalog has a column of SkyCoord objects.
    """
    ra = [149.0, 150.0, 151.0] * u.degree
    dec = [1.9, 2.0, 2.1] * u.degree
    x = [1, 2, 3]
    y = [4, 5, 6]

    # Success: SkyCoord instance
    tab = QTable({'coords': SkyCoord(ra=ra, dec=dec), 'x': x, 'y': y})
    ldr = deconfigged_helper.loaders['object']
    ldr.object = tab
    ldr.format = 'Catalog'
    importer = ldr.importer

    # make sure the coordinate columns were correctly identified
    assert isinstance(importer.input['coords'], SkyCoord)
    assert 'SkyCoord_RA' in importer.output.keys()
    assert 'SkyCoord_Dec' in importer.output.keys()


def test_pixcoord_column_detection(deconfigged_helper):
    """
    If a PixCoord object is passed to the catalog importer, it should ignore those columns.
    """
    ra = [149.0, 150.0, 151.0] * u.degree
    dec = [1.9, 2.0, 2.1] * u.degree
    x = [1, 2, 3]
    y = [4, 5, 6]

    # Failure: PixCoord instance
    tab = QTable({'coords': SkyCoord(ra=ra, dec=dec), 'pix': PixCoord(x=x, y=y)})
    ldr = deconfigged_helper.loaders['object']
    ldr.object = tab
    ldr.format = 'Catalog'
    importer = ldr.importer

    # make sure x and y are ignored
    assert 'pix' not in importer.output.keys()


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
