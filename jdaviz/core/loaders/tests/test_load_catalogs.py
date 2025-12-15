import os

from astropy.coordinates import SkyCoord
from astropy.table import Table, QTable
from astropy.tests.helper import assert_quantity_allclose
from astropy.io import fits
from astropy.nddata import NDData
import astropy.units as u
import numpy as np
import pytest


def _make_catalog(with_units=True, as_skycoord=False):
    """
    Create a sample catalog table with optional units and SkyCoord columns
    for testing purposes.
    """

    ra = [9.423, 9.421, 9.415] * (u.deg if with_units else 1)
    dec = [-33.711, -33.716, -33.717] * (u.deg if with_units else 1)
    obj_id = ['source1', 'souce2', 'source3']
    flux = [10, 20, 30] * (u.Jy if with_units else 1)

    tab_cls = QTable if with_units else Table

    if as_skycoord:
        sc = SkyCoord(ra, dec)
        return tab_cls(data=[sc, obj_id, flux], names=['SkyCoord', 'Obj_ID', 'flux'])
    return tab_cls(data=[ra, dec, obj_id, flux],
                   names=['RA', 'Dec', 'Obj_ID', 'flux'])


def _make_catalog_xy_radec(with_units=True):

    ra = [337.52274, 337.48273, 337.48296, 337.52333] * (u.deg if with_units else 1)
    dec = [-20.80742, -20.80741, -20.82380, -20.82425] * (u.deg if with_units else 1)
    x = [-7.27571754, 127.36624541, 126.57857853, -9.26004303]
    y = [94.28695926, 94.30831263, 35.30447687, 33.69891921]
    obj_id = ['source1', 'source2', 'source3', 'source4']
    flux = [10, 20, 30, 40] * (u.Jy if with_units else 1)

    tab_cls = QTable if with_units else Table

    return tab_cls(data=[ra, dec, x, y, obj_id, flux],
                   names=['RA', 'Dec', 'X', 'Y', 'Obj_ID', 'flux'])


def _make_catalog_string_coord_columns():
    # complelete nonsense coordinates, just care about parsing the units
    ra = ['5° 55′ 55″', '5° 55′ 55″', '5° 55′ 55″']
    dec = ['4° 44′ 44″', '4° 44′ 44″', '4° 44′ 44″']
    x = ['1', '2', '3']
    y = ['4', '5', '6']
    obj_id = ['source1', 'souce2', 'source3']
    flux = [10, 20, 30] * u.Jy

    return QTable(data=[ra, dec, x, y, obj_id, flux],
                  names=['RA', 'Dec', 'X', 'Y', 'Obj_ID', 'flux'])


def _make_catalog_no_coordinates():
    # Table to test loading catalogs that aren't 'Source Catalogs',
    col1 = ['A', 'B', 'C']
    col2 = [1, 2, 3]
    col3 = [True, False, True]

    return Table(data=[col1, col2, col3],
                 names=['col1', 'col2', 'col3'])


def test_load_catalog_no_source_positions(imviz_helper, image_2d_wcs):
    """
    A table should be able to be loaded without selecting
    an RA/Dec or X/Y pair. This table will not have the functionality
    of a 'Souce Catalog' that does have source positions
    (linking, mouseover) but it may be loaded to plot for example
    in the scatter or histrogram viewer.
    """
    imviz_helper.app.state.catalogs_in_dc = True

    catalog_obj = _make_catalog_no_coordinates()

    # load data so we can test orientation later
    data = NDData(np.ones((128, 128)), wcs=image_2d_wcs)
    imviz_helper.load(data)

    # load catalog, all columns
    imviz_helper.load(catalog_obj, col_other=['col1', 'col2', 'col3'])

    # check for the table in the data collection
    dc = imviz_helper.app.data_collection
    assert len(dc) == 2
    assert 'Catalog' in imviz_helper.app.data_collection.labels
    tab = imviz_helper.app.data_collection[1].get_object(Table)
    assert 'col1' in tab.colnames

    # make sure linking doesn't produce any errors when alingment changes.
    # this isn't relevant for this catalog with no source positons,
    # but orientation will check for the presence of certain
    # components in a table to decide not to link and we
    # want to make sure that works correctly
    imviz_helper.plugins['Orientation'].align_by = 'WCS'


def test_load_catalog_with_string_coord_cols(imviz_helper):
    """
    Test loading a catalog with string RA/Dec columns (that can be converted
    into units, e.g string representation of hourangle units) into the
    Imviz helper."""

    imviz_helper.app.state.catalogs_in_dc = True

    catalog_obj = _make_catalog_string_coord_columns()

    # load catalog
    imviz_helper.load(catalog_obj)

    dc = imviz_helper.app.data_collection
    assert len(dc) == 1
    assert 'Catalog' in imviz_helper.app.data_collection.labels

    # make coordinate columns were renamed to Right Ascension and Declination,
    # X and Y in the data collection for consistency, and that RA / Dec always
    # has units
    qtab = dc[0].get_object(QTable)
    assert 'RA' in qtab.colnames
    assert 'Dec' in qtab.colnames
    assert 'X' in qtab.colnames
    assert 'Y' in qtab.colnames
    # make sure only ra/dec/x/y/index loaded, since we didn't specify more columns
    assert len(qtab.colnames) == 5
    # and that it has the correct contents, and always has units assigned
    # when data is loaded from a unitless table, units should always be assigned
    # to the catalog in the data collection based on selections in the loader

    # go through SkyCoord to parse weird string format into deg units for comparison
    sc = SkyCoord(ra=catalog_obj['RA'], dec=catalog_obj['Dec'])

    assert_quantity_allclose(qtab['RA'], sc.ra.deg * u.deg)
    assert_quantity_allclose(qtab['Dec'], sc.dec.deg * u.deg)

    # cast data collection X/Y back to strings for comparison
    assert np.all(qtab['X'].astype(str) == catalog_obj['X'])
    assert np.all(qtab['Y'].astype(str) == catalog_obj['Y'])


@pytest.mark.parametrize("from_file", [True, False])
@pytest.mark.parametrize("with_units", [True, False])
def test_load_catalog_xy_and_radec(imviz_helper, tmp_path, from_file, with_units):

    imviz_helper.app.state.catalogs_in_dc = True

    catalog_obj = _make_catalog_xy_radec(with_units=True)

    if from_file:
        fn = os.path.join(tmp_path, "catalog.ecsv")
        catalog_obj.write(fn)
        catalog = fn
    else:
        catalog = catalog_obj

    # load catalog
    imviz_helper.load(catalog)

    dc = imviz_helper.app.data_collection
    assert len(dc) == 1
    assert 'Catalog' in imviz_helper.app.data_collection.labels

    # make sure 'RA' column was renamed to Right Ascension and 'Dec' to 'Declination'
    # in the data collection for consistency, and that the table in the data
    # collection always has units
    qtab = imviz_helper.app.data_collection[0].get_object(QTable)
    assert 'RA' in qtab.colnames
    assert 'Dec' in qtab.colnames
    assert 'X' in qtab.colnames
    assert 'Y' in qtab.colnames

    # make sure only ra/dec/x/y/index loaded, since we didn't specify more columns
    assert len(qtab.colnames) == 5
    # and that it has the correct contents
    assert_quantity_allclose(qtab['RA'], catalog_obj['RA'])
    assert_quantity_allclose(qtab['Dec'], catalog_obj['Dec'])
    assert_quantity_allclose(qtab['X'], catalog_obj['X'])
    assert_quantity_allclose(qtab['Y'], catalog_obj['Y'])


def test_import_enabled_disabled(imviz_helper):
    """
    Verify that when no coordinate column pair (RA/Dec or X/Y) is selected,
    importing is disabled, when at least one coordinate column pair is selected
    importing is enabled, and when RA is selected but Dec is not (and vice versa,
    along with the same logic for X/Y) importing is disabled.
    """

    imviz_helper.app.state.catalogs_in_dc = True

    catalog_obj = _make_catalog_xy_radec(with_units=True)

    loaders = imviz_helper.loaders
    ldr = loaders['object']
    ldr.object = catalog_obj

    ldr.format = 'Catalog'
    ldr.importer.col_ra.selected = '---'
    ldr.importer.col_dec.selected = '---'
    ldr.importer.col_x.selected = '---'
    ldr.importer.col_y.selected = '---'
    # no coordinate column pair selected, import should still be enabled
    assert ldr.importer._obj.import_disabled is False

    # when RA is selected but Dec is not, import should be disabled
    ldr.importer.col_ra.selected = 'RA'
    assert ldr.importer._obj.import_disabled is True
    # and then when Dec is selected too, import should be enabled
    ldr.importer.col_dec.selected = 'Dec'
    assert ldr.importer._obj.import_disabled is False

    # reset and test the same logic for X/Y
    ldr.importer.col_ra.selected = '---'
    ldr.importer.col_dec.selected = '---'
    ldr.importer.col_x.selected = 'X'
    ldr.importer.col_y.selected = '---'
    # now with no coordinate column pair selected, import should be disabled
    assert ldr.importer._obj.import_disabled is True
    # when Y is selected too, import should be enabled
    ldr.importer.col_y.selected = 'Y'
    assert ldr.importer._obj.import_disabled is False


@pytest.mark.parametrize("from_file", [True, False])
@pytest.mark.parametrize("with_units", [True, False])
def test_load_catalog(imviz_helper, image_2d_wcs, tmp_path, from_file, with_units):
    """
    Verify the basic functionality loading catalogs into the data collection.
    Test cases cover both in-memory Astropy tables and ECSV files, and catalogs
    with and without units on RA/Dec columns already assigned.
    """
    imviz_helper.app.state.catalogs_in_dc = True

    # basic catalog with RA, Dec, ID, and Flux columns and units
    catalog_obj = _make_catalog(with_units)

    if from_file:
        fn = os.path.join(tmp_path, "catalog.ecsv")
        catalog_obj.write(fn)
        catalog = fn
    else:
        catalog = catalog_obj

    # load image and align by WCS so loading the catalog will run through the
    # linking code to test it
    data = NDData(np.ones((128, 128)), wcs=image_2d_wcs)
    imviz_helper.load(data)
    imviz_helper.plugins['Orientation'].align_by = 'WCS'

    # load catalog
    imviz_helper.load(catalog)

    # ensure that it is in the data collection with the correct label "Catalog"
    dc = imviz_helper.app.data_collection
    assert len(dc) == 3  # image, orientation layer, and catalog
    assert 'Catalog' in imviz_helper.app.data_collection.labels

    # make sure 'RA' column was renamed to Right Ascension and 'Dec' to 'Declination'
    # in the data collection for consistency, and that the table in the data
    # collection always has units
    qtab = imviz_helper.app.data_collection[-1].get_object(QTable)
    assert 'RA' in qtab.colnames
    assert 'Dec' in qtab.colnames
    # there should also be an ID column
    assert 'ID' in qtab.colnames
    # we didn't specify a specific ID column, so it should just be the index
    # of each source
    assert np.all(qtab['ID'] == np.arange(len(catalog_obj)))
    # make sure only ra and dec (plus index) loaded, since we didn't specify more columns
    assert len(qtab.colnames) == 3
    # and that it has the correct contents, and always has units assigned
    # when data is loaded from a unitless table, units should always be assigned
    # to the catalog in the data collection based on selections in the loader
    un = 1
    if not with_units:
        un = u.deg
    assert_quantity_allclose(qtab['RA'], catalog_obj['RA'] * un)
    assert_quantity_allclose(qtab['Dec'], catalog_obj['Dec'] * un)
    assert qtab['RA'].unit == qtab['Dec'].unit == u.deg

    # make sure 'col_ra_has_unit' is True if the input catalog has units, and is
    # False if the input doesn't have units. This controls the dropdown to
    # select unit is exposed, which is eventually assigned to the table column
    # in the data collection
    ldr = imviz_helper.loaders['file' if from_file else 'object']
    setattr(ldr, 'filepath' if from_file else 'object', catalog)
    assert ldr.importer._obj.col_ra_has_unit == with_units

    # load it again, make sure label incremented by 1
    imviz_helper.load(catalog)
    assert len(dc) == 4  # image, orientation layer, and 2 catalogs
    assert 'Catalog (1)' in imviz_helper.app.data_collection.labels

    # load with custom label and check label
    imviz_helper.load(catalog, data_label='my_catalog')
    assert len(dc) == 5  # image, orientation layer, and 3 catalogs
    assert 'my_catalog' in imviz_helper.app.data_collection.labels

    # test other loader API options. switch RA and Dec col just to test
    # non-default column selection
    imviz_helper.load(catalog, data_label='with_flux', col_other='flux',
                      col_ra='Dec', col_dec='RA')
    assert len(dc) == 6  # image, orientation layer, and 4 catalogs
    assert 'flux' in dc['with_flux'].get_object(QTable).colnames
    qtab = imviz_helper.app.data_collection[-1].get_object(QTable)
    assert_quantity_allclose(qtab['RA'], catalog_obj['RA'] * un)
    assert_quantity_allclose(qtab['Dec'], catalog_obj['Dec'] * un)


@pytest.mark.parametrize("from_file", [True, False])
def test_load_catalog_skycoord(imviz_helper, tmp_path, from_file):
    """
    Test loading a catalog with a SkyCoord column into the Imviz helper.

    This test verifies that when a catalog containing a SkyCoord column is
    loaded, the loader correctly uses this column as the default for
    Right Ascension (RA) and Declination (Dec).
    """
    # test loading catalog with SkyCoord column, which should be used
    # as default for Ra and Dec

    imviz_helper.app.state.catalogs_in_dc = True

    catalog_obj = _make_catalog(as_skycoord=True)

    if from_file:
        fn = os.path.join(tmp_path, "catalog.ecsv")
        catalog_obj.write(fn)
        catalog = fn
    else:
        catalog = catalog_obj

    # load catalog
    imviz_helper.load(catalog)

    dc = imviz_helper.app.data_collection
    assert len(dc) == 1
    assert 'Catalog' in imviz_helper.app.data_collection.labels

    qtab = imviz_helper.app.data_collection[0].get_object(QTable)
    assert 'SkyCoord_RA' in qtab.colnames
    assert 'SkyCoord_Dec' in qtab.colnames
    # make sure only ra and dec (plus index) loaded, since we didn't specify more columns
    assert len(qtab.colnames) == 3
    # and that it has the correct contents, and always has units assigned
    # when data is loaded from a unitless table, units should always be assigned
    # to the catalog in the data collection based on selections in the loader
    assert_quantity_allclose(qtab['SkyCoord_RA'], catalog_obj['SkyCoord'].ra)
    assert_quantity_allclose(qtab['SkyCoord_Dec'], catalog_obj['SkyCoord'].dec)


@pytest.mark.remote_data
def test_astroquery_load_catalog_source(deconfigged_helper, catch_validate_known_exceptions):
    deconfigged_helper.app.state.catalogs_in_dc = True

    ldr = deconfigged_helper.loaders['astroquery']
    ldr.source = 'M4'
    ldr.telescope = 'Gaia'
    ldr.max_results = 10
    # TODO: remove catch_validate_known_exception
    #  when GAIA completes system maintenance (December 10, 2025 9:00 CET,
    #  this has so far proven to be a moving target...)
    # Use exception context manager to handle occasional VOTable parsing
    # errors via retrieval failures and HTTP 500 errors. Both currently due
    # to scheduled maintenance. These errors are reported as (and caught):
    # 'File does not appear to be a VOTABLE' / HTTPError: Error 500
    from astropy.io.votable.exceptions import E19
    from requests.exceptions import HTTPError
    with catch_validate_known_exceptions((E19, HTTPError, TimeoutError),
                                         stdout_text_to_check='maintenance'):
        ldr.query_archive()
    assert 'Catalog' in ldr.format.choices
    ldr.format = 'Catalog'

    ldr.importer.col_id = 'source_id'
    ldr.importer.col_other = ['parallax', 'pm', 'bp_rp', 'phot_rp_mean_mag']
    ldr.importer.viewer.create_new = 'Scatter'
    ldr.load()
    assert 'Scatter' in deconfigged_helper.viewers
    assert 'Catalog' in deconfigged_helper.viewers['Scatter'].data_menu.layer.choices


@pytest.mark.remote_data
def test_astroquery_load_catalog_from_viewer(deconfigged_helper):
    deconfigged_helper.app.state.catalogs_in_dc = True
    arr = np.ones((1489, 2048))

    # header is based on the data provided above
    hdu1 = fits.ImageHDU(arr, name='SCI')
    hdu1.header.update({'CTYPE1': 'RA---TAN',
                        'CUNIT1': 'deg',
                        'CD1_1': -7.80378407867e-05,
                        'CD1_2': 7.74904339463e-05,
                        'CRPIX1': 1025.0,
                        'CRVAL1': 6.62750450757,
                        'NAXIS1': 2048,
                        'CTYPE2': 'DEC--TAN',
                        'CUNIT2': 'deg',
                        'CD2_1': 7.74973322238e-05,
                        'CD2_2': 7.80788034973e-05,
                        'CRPIX2': 745.0,
                        'CRVAL2': 1.54470013629,
                        'NAXIS2': 1489})
    deconfigged_helper.load(hdu1, format='Image', data_label='has_wcs')

    ldr = deconfigged_helper.loaders['astroquery']
    ldr.viewer = list(deconfigged_helper.viewers.keys())[0]
    ldr.telescope = 'SDSS'
    ldr.max_results = 10
    ldr.query_archive()
    assert 'Catalog' in ldr.format.choices
    ldr.format = 'Catalog'


def test_invalid(imviz_helper, tmp_path):

    imviz_helper.app.state.catalogs_in_dc = True

    # make sure you can't load an empty table
    empty_table = Table()

    # empty table from object
    ldr = imviz_helper.loaders['object']
    ldr.object = empty_table
    assert 'Catalog' not in ldr.format.choices

    # empty table from file
    fn = os.path.join(tmp_path, "empty_catalog.ecsv")
    empty_table.write(fn)

    ldr = imviz_helper.loaders['file']
    ldr.filepath = fn
    assert 'Catalog' not in ldr.format.choices

    # while a fits file can be opened with table.read, it should not be
    # validated as a Catalog
    ldr = imviz_helper.loaders['object']
    ldr.object = fits.ImageHDU(np.ones((32, 25)))
    assert 'Image' in ldr.format.choices
    assert 'Catalog' not in ldr.format.choices


def test_scatter_viewer(deconfigged_helper):
    deconfigged_helper.app.state.catalogs_in_dc = True

    ldr = deconfigged_helper.loaders['object']
    ldr.object = _make_catalog(with_units=True)
    ldr.format = 'Catalog'

    assert 'Scatter' in ldr.importer.viewer.create_new.choices
    ldr.importer.viewer.create_new = 'Scatter'
    ldr.load()

    assert 'Scatter' in deconfigged_helper.viewers
    assert 'Scatter' in deconfigged_helper.new_viewers

    nv = deconfigged_helper.new_viewers['Scatter']
    nv.dataset = ['Catalog']
    nv.viewer_label = 'Added Scatter Viewer'
    nv()

    assert 'Added Scatter Viewer' in deconfigged_helper.viewers


def test_histogram_viewer(deconfigged_helper):
    deconfigged_helper.app.state.catalogs_in_dc = True

    ldr = deconfigged_helper.loaders['object']
    ldr.object = _make_catalog(with_units=True)
    ldr.format = 'Catalog'
    ldr.importer.col_other = ['flux']

    assert 'Histogram' in ldr.importer.viewer.create_new.choices
    ldr.importer.viewer.create_new = 'Histogram'
    ldr.load()

    assert 'Histogram' in deconfigged_helper.viewers
    assert 'Histogram' in deconfigged_helper.new_viewers

    nv = deconfigged_helper.new_viewers['Histogram']
    nv.dataset = ['Catalog']
    nv.xatt = 'flux'
    nv.viewer_label = 'Added Histogram Viewer'
    nv()

    assert 'Added Histogram Viewer' in deconfigged_helper.viewers

    po = deconfigged_helper.plugins['Plot Options']
    po.viewer = 'Added Histogram Viewer'
    po.xatt = 'RA'

    assert str(deconfigged_helper.viewers['Histogram']._obj.glue_viewer.state.x_att) == 'RA'  # noqa


def test_table_viewer(deconfigged_helper):
    deconfigged_helper.app.state.catalogs_in_dc = True

    ldr = deconfigged_helper.loaders['object']
    ldr.object = _make_catalog(with_units=True)
    ldr.format = 'Catalog'
    ldr.importer.viewer.create_new = 'Table'
    ldr.load()

    assert len(deconfigged_helper.viewers) == 1  # Table viewer created upon load
    tv = deconfigged_helper.viewers['Table']
    assert len(tv._obj.glue_viewer.layers) == 1

    # create another viewer through viewer creator
    vc = deconfigged_helper.new_viewers['Table']
    vc.dataset.select_all()
    nv = vc()

    assert len(deconfigged_helper.viewers) == 2
    assert len(nv._obj.glue_viewer.layers) == 1

    # subset creation tool should not be visible because no entries checked
    toolbar = tv._obj.glue_viewer.toolbar
    assert toolbar.tools['jdaviz:table_subset'].is_visible() is False

    tv._obj.glue_viewer.widget_table.checked = [1, 2]

    toolbar.select_tool('jdaviz:table_subset')
    assert 'Subset 1' in deconfigged_helper.plugins['Subset Tools'].subset.choices

    assert toolbar.tools['jdaviz:table_subset'].is_visible() is True
    tv._obj.glue_viewer.widget_table.checked = []
    assert toolbar.tools['jdaviz:table_subset'].is_visible() is False


def test_catalog_visibility(imviz_helper, image_2d_wcs):
    """

    # Verify that catalog visibility is toggled on/off correctly
    # based on link type and presence of pixel and/or world coordinates
    # in loaded catalog.
    """

    data = NDData(np.ones((128, 128)), wcs=image_2d_wcs)
    imviz_helper.load(data)

    # catalog with ra, dec, x, y
    orig_catalog = _make_catalog_xy_radec(with_units=True)
    # catalog with ra, dec only
    table_ra_dec_only = orig_catalog['RA', 'Dec', 'Obj_ID']
    # catalog with x, y only
    table_x_y_only = orig_catalog['X', 'Y', 'Obj_ID']

    imviz_helper.app.state.catalogs_in_dc = True
    imviz_helper.load(table_ra_dec_only,
                      data_label='catalog0')

    # since we're pixel linked and catalog has only world coordinates,
    # visiblity should be off by default
    dm = imviz_helper.viewers['imviz-0'].data_menu
    assert dm.data_labels_visible == ['Image[DATA]']

    # but if we load the catalog with X, Y, it should be visible
    imviz_helper.load(table_x_y_only,
                      data_label='catalog1')
    assert dm.data_labels_visible == ['catalog1', 'Image[DATA]']

    # now change to WCS linking
    imviz_helper.plugins['Orientation'].align_by = 'WCS'

    # load catalog with RA, Dec only again. It's default visiblity should
    # now be on since we're WCS linked
    imviz_helper.load(table_ra_dec_only,
                      data_label='catalog2')

    # the pixel-only 'catalog1' should now be hidden
    assert dm.data_labels_visible == ['catalog2', 'Image[DATA]']

    # loading a pixel-coordinate-only catalog should now be hidden by default
    # since were WCS linked
    imviz_helper.load(table_x_y_only,
                      data_label='catalog3')
    assert 'catalog3' not in dm.data_labels_visible
