import os

from astropy.coordinates import SkyCoord
from astropy.table import Table, QTable
from astropy.tests.helper import assert_quantity_allclose
from astropy.io import fits
import astropy.units as u
import numpy as np
import pytest


def _make_catalog(with_units=u.deg, as_skycoord=False):
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


@pytest.mark.parametrize("from_file", [True, False])
@pytest.mark.parametrize("with_units", [True, False])
def test_load_catalog(imviz_helper, tmp_path, from_file, with_units):
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

    # load catalog
    imviz_helper.load(catalog)

    # ensure that it is in the data collection with the correct label "Catalog"
    dc = imviz_helper.app.data_collection
    assert len(dc) == 1
    assert 'Catalog' in imviz_helper.app.data_collection.labels

    # make sure 'RA' column was renamed to Right Ascension and 'Dec' to 'Declination'
    # in the data collection for consistency, and that the table in the data
    # collection always has units
    qtab = imviz_helper.app.data_collection[0].get_object(QTable)
    assert 'Right Ascension' in qtab.colnames
    assert 'Declination' in qtab.colnames
    # make sure only ra and dec loaded, since we didn't specify more columns
    assert len(qtab.colnames) == 2
    # and that it has the correct contents, and always has units assigned
    # when data is loaded from a unitless table, units should always be assigned
    # to the catalog in the data collection based on selections in the loader
    un = 1
    if not with_units:
        un = u.deg
    assert_quantity_allclose(qtab['Right Ascension'], catalog_obj['RA'] * un)
    assert_quantity_allclose(qtab['Declination'], catalog_obj['Dec'] * un)
    assert qtab['Right Ascension'].unit == qtab['Declination'].unit == u.deg

    # make sure 'col_ra_has_unit' is True if the input catalog has units, and is
    # False if the input doesn't have units. This controls the dropdown to
    # select unit is exposed, which is eventually assigned to the table column
    # in the data collection
    ldr = imviz_helper.loaders['file' if from_file else 'object']
    setattr(ldr, 'filepath' if from_file else 'object', catalog)
    assert ldr.importer._obj.col_ra_has_unit == with_units

    # load it again, make sure label incremented by 1
    imviz_helper.load(catalog)
    assert len(dc) == 2
    assert 'Catalog (1)' in imviz_helper.app.data_collection.labels

    # load with custom label and check label
    imviz_helper.load(catalog, data_label='my_catalog')
    assert len(dc) == 3
    assert 'my_catalog' in imviz_helper.app.data_collection.labels

    # test other loader API options. switch RA and Dec col just to test
    # non-default column selection
    imviz_helper.load(catalog, data_label='with_flux', col_other='flux',
                      col_ra='Dec', col_dec='RA')
    assert len(dc) == 4
    assert 'flux' in dc['with_flux'].get_object(QTable).colnames
    qtab = imviz_helper.app.data_collection[-1].get_object(QTable)
    assert_quantity_allclose(qtab['Right Ascension'], catalog_obj['Dec'] * un)
    assert_quantity_allclose(qtab['Declination'], catalog_obj['RA'] * un)


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

    # make sure 'RA' column was renamed to Right Ascension and 'Dec' to 'Declination'
    # in the data collection for consistency, and that the table in the data
    # collection always has units
    qtab = imviz_helper.app.data_collection[0].get_object(QTable)
    assert 'Right Ascension' in qtab.colnames
    assert 'Declination' in qtab.colnames
    # make sure only ra and dec loaded, since we didn't specify more columns
    assert len(qtab.colnames) == 2
    # and that it has the correct contents, and always has units assigned
    # when data is loaded from a unitless table, units should always be assigned
    # to the catalog in the data collection based on selections in the loader
    assert_quantity_allclose(qtab['Right Ascension'], catalog_obj['SkyCoord'].ra)
    assert_quantity_allclose(qtab['Declination'], catalog_obj['SkyCoord'].dec)


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
