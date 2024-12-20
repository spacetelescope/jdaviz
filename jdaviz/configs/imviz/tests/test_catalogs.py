'''
This file tests four tasks of the catalogs.py plugin in Imviz.
1. When no image/data is provided, the search does not crash
- Additionally there are no results available as the search did not occur
2. When an image/data is provided, specifically with no results being found,
results are available and are set to 0
3. When an image/data is provided, specifically with results being found,
results are available and are set to > 0
4. When the markers are cleared, there are no results available

The data used for testing are provided in the comments below.

Currently, these tests are driven by an SDSS search.
As more catalogs are added to the plugin, each test will need to be
specific based on the respective catalog.

Additionally, tests that check for results > 0 are correct as the data was
found from an SDSS server (and therefore should have results).
However, the number of results is determined on the belief that the search
is correct and the removal of the points outside the zoom limits is correctly done.
This may need to instead be tested for in the future.
'''

import numpy as np
from numpy.testing import assert_allclose
import pytest

from astropy.coordinates import SkyCoord
from astropy.io import fits
from astropy.nddata import NDData
from astropy.table import Table, QTable


@pytest.mark.remote_data
class TestCatalogs:
    # testing that the plugin search does not crash when no data/image is provided
    def test_plugin_no_image(self, imviz_helper):
        catalogs_plugin = imviz_helper.plugins["Catalog Search"]._obj
        catalogs_plugin.plugin_opened = True
        # running the search without any data loaded into Imviz
        catalogs_plugin.vue_do_search()

        assert not catalogs_plugin.results_available

    # testing that variables update correctly when the image/data provided does not have results
    def test_plugin_image_no_result(self, imviz_helper, image_2d_wcs):
        arr = np.ones((10, 10))
        ndd = NDData(arr, wcs=image_2d_wcs)

        imviz_helper.load_data(ndd, data_label='no_results_data')

        catalogs_plugin = imviz_helper.plugins["Catalog Search"]._obj
        catalogs_plugin.plugin_opened = True
        catalogs_plugin.vue_do_search()

        # number of results should be 0
        assert catalogs_plugin.results_available
        assert catalogs_plugin.number_of_results == 0

    # testing that every variable updates correctly when the image/data provided does have results
    # data used: information based on this image -
    # https://dr12.sdss.org/fields/runCamcolField?field=76&camcol=5&run=7674
    # the z-band FITS image was downloaded and used
    # NOTE: We mark "slow" so it only runs on the dev job that is allowed to fail.
    @pytest.mark.slow
    def test_plugin_image_with_result(self, imviz_helper, tmp_path):
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
        imviz_helper.load_data(hdu1, data_label='has_wcs')

        catalogs_plugin = imviz_helper.plugins["Catalog Search"]._obj
        catalogs_plugin.plugin_opened = True

        # test SDSS catalog
        catalogs_plugin.catalog.selected = 'SDSS'

        # testing that SDSS catalog respects the maximum sources set
        catalogs_plugin.max_sources = 100
        catalogs_plugin.search(error_on_fail=True)

        assert catalogs_plugin.results_available
        assert catalogs_plugin.number_of_results == catalogs_plugin.max_sources

        # reset max_sources to it's default value
        catalogs_plugin.max_sources = 1000
        # This basically calls the following under the hood:
        #   skycoord_center = SkyCoord(6.62754354, 1.54466139, unit="deg")
        #   zoom_radius = r_max = 3 * u.arcmin
        #   query_region_result = SDSS.query_region(skycoord_center, radius=zoom_radius, ...)
        catalogs_plugin.search(error_on_fail=True)

        assert catalogs_plugin.catalog.selected == 'SDSS'

        # number of results should be > 500 or so
        # Answer was determined by running the search with the image in the notebook.
        assert catalogs_plugin.results_available
        assert catalogs_plugin.number_of_results > 500
        prev_results = catalogs_plugin.number_of_results

        # testing that every variable updates accordingly when markers are cleared
        catalogs_plugin.vue_do_clear()

        assert not catalogs_plugin.results_available

        # test loading from file
        table = imviz_helper.app._catalog_source_table
        qtable = QTable({'sky_centroid': SkyCoord(table['ra'], table['dec'], unit='deg'),
                         'label': table['objid']})
        tmp_file = tmp_path / 'test.ecsv'
        qtable.write(tmp_file, overwrite=True)

        # reset max_sources to it's default value
        catalogs_plugin.max_sources = 1000

        catalogs_plugin.from_file = str(tmp_file)
        # setting filename from API will automatically set catalog to 'From File...'
        assert catalogs_plugin.catalog.selected == 'From File...'
        catalogs_plugin.search(error_on_fail=True)
        assert catalogs_plugin.results_available
        assert catalogs_plugin.number_of_results == prev_results

        catalogs_plugin.table.selected_rows = catalogs_plugin.table.items[0:2]
        assert len(catalogs_plugin.table.selected_rows) == 2

        # test Gaia catalog
        catalogs_plugin.catalog.selected = 'Gaia'

        assert catalogs_plugin.catalog.selected == 'Gaia'

        # astroquery.gaia query has the Gaia.ROW_LIMIT parameter that limits the number of rows
        # returned. Test to verify that this query functionality is maintained by the package.
        # Note: astroquery.sdss does not have this parameter.
        catalogs_plugin.max_sources = 10
        with pytest.warns(ResourceWarning):
            catalogs_plugin.search(error_on_fail=True)

        assert catalogs_plugin.results_available
        assert catalogs_plugin.number_of_results == catalogs_plugin.max_sources

        assert imviz_helper.viewers['imviz-0']._obj.state.x_min == -0.5
        assert imviz_helper.viewers['imviz-0']._obj.state.x_max == 2047.5
        assert imviz_helper.viewers['imviz-0']._obj.state.y_min == -0.5
        assert imviz_helper.viewers['imviz-0']._obj.state.y_max == 1488.5

        # set 'padding' to reproduce original hard-coded 50 pixel window
        # so test results don't change
        catalogs_plugin.zoom_to_selected(padding=50 / 2048)

        assert imviz_helper.viewers['imviz-0']._obj.state.x_min == 858.24969
        assert imviz_helper.viewers['imviz-0']._obj.state.x_max == 958.38461
        assert imviz_helper.viewers['imviz-0']._obj.state.y_min == 278.86265
        assert imviz_helper.viewers['imviz-0']._obj.state.y_max == 378.8691


def test_from_file_parsing(imviz_helper, tmp_path):
    catalogs_plugin = imviz_helper.plugins["Catalog Search"]._obj

    # _on_file_path_changed is fired when changing the selection in the file dialog
    catalogs_plugin.catalog._on_file_path_changed({'new': './invalid_path'})
    assert catalogs_plugin.from_file_message == 'File path does not exist'

    # observe('from_file') is fired when setting from_file from the API or via import_file
    # (or after clicking select in the file dialog)
    with pytest.raises(ValueError, match='./invalid_path is not a valid file path'):
        catalogs_plugin.import_catalog('./invalid_path')

    # setting to a blank string from the API resets the catalog selection to the
    # default/first entry
    catalogs_plugin.from_file = ''
    assert catalogs_plugin.catalog.selected == catalogs_plugin.catalog.choices[0]

    not_table_file = tmp_path / 'not_table.tst'
    not_table_file.touch()
    catalogs_plugin.catalog._on_file_path_changed({'new': not_table_file})
    assert catalogs_plugin.from_file_message == 'Could not parse file with astropy.table.QTable.read'  # noqa

    qtable = QTable({'not_sky_centroid': [1, 2, 3]})
    not_valid_table = tmp_path / 'not_valid_table.ecsv'
    qtable.write(not_valid_table, overwrite=True)
    catalogs_plugin.catalog._on_file_path_changed({'new': not_valid_table})
    assert catalogs_plugin.from_file_message == 'Table does not contain required sky_centroid column'  # noqa


def test_offline_ecsv_catalog(imviz_helper, image_2d_wcs, tmp_path):
    sky = SkyCoord(ra=[337.5202807, 337.51909197, 337.51760596],
                   dec=[-20.83305528, -20.83222194, -20.83083304], unit='deg')
    tbl = QTable({'sky_centroid': sky})
    tbl_file = str(tmp_path / 'sky_centroid.ecsv')
    tbl.write(tbl_file, overwrite=True)
    n_entries = len(tbl)

    ndd = NDData(np.ones((10, 10)), wcs=image_2d_wcs)
    imviz_helper.load_data(ndd, data_label='data_with_wcs')
    assert len(imviz_helper.app.data_collection) == 1

    catalogs_plugin = imviz_helper.plugins['Catalog Search']._obj
    catalogs_plugin.from_file = tbl_file
    catalogs_plugin.catalog_selected = 'From File...'
    out_tbl = catalogs_plugin.search(error_on_fail=True)
    assert len(out_tbl) == n_entries
    assert catalogs_plugin.number_of_results == n_entries
    assert len(imviz_helper.app.data_collection) == 2  # image + markers

    catalogs_plugin.table.selected_rows = [catalogs_plugin.table.items[0]]
    assert len(catalogs_plugin.table.selected_rows) == 1

    # test to ensure sources searched for respect the maximum sources traitlet
    catalogs_plugin.max_sources = 1
    catalogs_plugin.search(error_on_fail=True)
    assert catalogs_plugin.number_of_results == catalogs_plugin.max_sources

    catalogs_plugin.clear_table()

    # test single source edge case and docs recommended input file type
    sky_coord = SkyCoord(ra=337.5202807, dec=-20.83305528, unit='deg')
    tbl = Table({'sky_centroid': [sky_coord], 'label': ['Source_1']})
    tbl_file = str(tmp_path / 'sky_centroid1.ecsv')
    tbl.write(tbl_file, overwrite=True)
    n_entries = len(tbl)

    catalogs_plugin.from_file = tbl_file
    out_tbl = catalogs_plugin.search()
    assert len([out_tbl]) == n_entries
    assert catalogs_plugin.number_of_results == n_entries
    assert len(imviz_helper.app.data_collection) == 2  # image + markers

    catalogs_plugin.clear()

    assert not catalogs_plugin.results_available
    assert len(imviz_helper.app.data_collection) == 2  # markers still there, just hidden

    catalogs_plugin.clear(hide_only=False)
    assert not catalogs_plugin.results_available
    assert len(imviz_helper.app.data_collection) == 1  # markers gone for good

    assert imviz_helper.viewers['imviz-0']._obj.state.x_min == -0.5
    assert imviz_helper.viewers['imviz-0']._obj.state.x_max == 9.5
    assert imviz_helper.viewers['imviz-0']._obj.state.y_min == -0.5
    assert imviz_helper.viewers['imviz-0']._obj.state.y_max == 9.5

    # test the zooming using the default 'padding' of 2% of the viewer size
    # around selected points
    catalogs_plugin.zoom_to_selected()
    assert imviz_helper.viewers['imviz-0']._obj.state.x_min == -0.19966
    assert imviz_helper.viewers['imviz-0']._obj.state.x_max == 0.20034000000000002
    assert imviz_helper.viewers['imviz-0']._obj.state.y_min == 0.8000100000000001
    assert imviz_helper.viewers['imviz-0']._obj.state.y_max == 1.20001


def test_zoom_to_selected(imviz_helper, image_2d_wcs, tmp_path):

    arr = np.ones((500, 500))
    ndd = NDData(arr, wcs=image_2d_wcs)
    imviz_helper.load_data(ndd)

    # write out catalog to file so we can read it back in
    # todo: if tables can be loaded directly at some point, do that

    # sources at pixel coords ~(100, 100), ~(200, 200)
    sky_coord = SkyCoord(ra=[337.49056532, 337.46086081],
                         dec=[-20.80555273, -20.7777673], unit='deg')
    tbl = Table({'sky_centroid': [sky_coord],
                 'label': ['Source_1', 'Source_2']})
    tbl_file = str(tmp_path / 'test_catalog.ecsv')
    tbl.write(tbl_file, overwrite=True)

    catalogs_plugin = imviz_helper.plugins['Catalog Search']

    catalogs_plugin._obj.from_file = tbl_file

    catalogs_plugin._obj.search()

    # select both sources
    catalogs_plugin._obj.table.selected_rows = catalogs_plugin._obj.table.items

    # check viewer limits before zoom
    xmin, xmax, ymin, ymax = imviz_helper.app._jdaviz_helper._default_viewer.get_limits()
    assert xmin == ymin == -0.5
    assert xmax == ymax == 499.5

    # zoom to selected sources
    catalogs_plugin.zoom_to_selected()

    # make sure the viewer bounds reflect the zoom, which, in pixel coords,
    # should be centered at roughly pixel coords (150, 150)
    xmin, xmax, ymin, ymax = imviz_helper.app._jdaviz_helper._default_viewer.get_limits()

    assert_allclose((xmin + xmax) / 2, 150., atol=0.1)
    assert_allclose((ymin + ymax) / 2, 150., atol=0.1)

    # and the zoom box size should reflect the default padding of 2% of the image
    # size around the bounding box containing the source(s), which in this case is
    # 10 pixels around
    assert_allclose(xmin, 100 - 10, atol=0.1)  # min x of selected sources minus pad
    assert_allclose(xmax, 200 + 10, atol=0.1)  # max x of selected sources plus pad
    assert_allclose(ymin, 100 - 10, atol=0.1)  # min y of selected sources minus pad
    assert_allclose(ymax, 200 + 10, atol=0.1)  # max y of selected sources plus pad

    # select one source now
    catalogs_plugin._obj.table.selected_rows = catalogs_plugin._obj.table.items[0:1]

    # zoom to single selected source, using a new value for 'padding'
    catalogs_plugin.zoom_to_selected(padding=0.05)

    # check that zoom window is centered correctly on the source at 100, 100
    xmin, xmax, ymin, ymax = imviz_helper.app._jdaviz_helper._default_viewer.get_limits()
    assert_allclose((xmin + xmax) / 2, 100., atol=0.1)
    assert_allclose((ymin + ymax) / 2, 100., atol=0.1)

    # and the zoom box size should reflect the default padding of 5% of the image
    # size around the bounding box containing the source(s), which in this case is
    # 25 pixels around
    assert_allclose(xmin, 100 - 25, atol=0.1)  # min x of selected source minus pad
    assert_allclose(xmax, 100 + 25, atol=0.1)  # max x of selected source plus pad
    assert_allclose(ymin, 100 - 25, atol=0.1)  # min y of selected source minus pad
    assert_allclose(ymax, 100 + 25, atol=0.1)  # max y of selected source plus pad

    # test that appropriate error is raised when padding is not a valud percentage
    with pytest.raises(ValueError, match="`padding` must be between 0 and 1."):
        catalogs_plugin.zoom_to_selected(padding=5)
