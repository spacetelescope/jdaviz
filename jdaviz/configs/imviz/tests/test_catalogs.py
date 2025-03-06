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

        # Since we are not really displaying, need this to test zoom.
        viewer = imviz_helper.default_viewer._obj
        viewer.shape = (100, 100)
        viewer.state._set_axes_aspect_ratio(1)

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

        # Zoom in so we have to filter sources outside the viewer bounds
        viewer = imviz_helper.app.get_viewer('imviz-0')
        viewer.state.x_min = 800
        viewer.state.x_max = 1200
        viewer.state.y_min = 800
        viewer.state.y_max = 1200

        catalogs_plugin.search(error_on_fail=True)

        assert catalogs_plugin.catalog.selected == 'SDSS'

        assert catalogs_plugin.results_available
        assert catalogs_plugin.number_of_results == 136
        prev_results = catalogs_plugin.number_of_results
        last_row = catalogs_plugin.table.items[-1]
        last_ra = float(last_row['Right Ascension (degrees)'])
        coords = viewer.state.reference_data.coords
        table_calc_ra = coords.pixel_to_world(float(last_row['x_coord']), float(last_row['y_coord'])).ra.value  # noqa
        assert_allclose(last_ra, table_calc_ra, rtol=0.00001)
        assert_allclose(last_ra, imviz_helper.app._catalog_source_table[-1]['ra'], atol=0.0001)  # noqa

        # testing that every variable updates accordingly when markers are cleared
        catalogs_plugin.clear_table()

        # Default zoom for the rest of the tests
        viewer.state.x_min = -0.5
        viewer.state.x_max = 2047.5
        viewer.state.y_min = -0.5
        viewer.state.y_max = 1488.5

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

        catalogs_plugin.select_rows(slice(0, 2))
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

        assert imviz_helper.viewers['imviz-0']._obj.state.x_min == 279.0
        assert imviz_helper.viewers['imviz-0']._obj.state.x_max == 1768.0
        assert imviz_helper.viewers['imviz-0']._obj.state.y_min == -0.5
        assert imviz_helper.viewers['imviz-0']._obj.state.y_max == 1488.5

        # Re-populate the table with a new search
        with pytest.warns(ResourceWarning):
            catalogs_plugin.search(error_on_fail=True)
        # Ensure at least one row is selected before zooming
        catalogs_plugin.table.selected_rows = [catalogs_plugin.table.items[0]]
        assert len(catalogs_plugin.table.selected_rows) > 0

        # set 'padding' to reproduce original hard-coded 50 pixel window
        # so test results don't change
        catalogs_plugin.zoom_to_selected(padding=50 / 2048)

        assert_allclose(
            imviz_helper.viewers['imviz-0']._obj.state.x_min, 1046.377555, atol=0.1)
        assert_allclose(
            imviz_helper.viewers['imviz-0']._obj.state.x_max, 1098.748805, atol=0.1)
        assert_allclose(
            imviz_helper.viewers['imviz-0']._obj.state.y_min, 699.110485, atol=0.1)
        assert_allclose(
            imviz_helper.viewers['imviz-0']._obj.state.y_max, 751.481735, atol=0.1)


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


def test_offline_ecsv_catalog(imviz_helper, image_2d_wcs):
    # Since we are not really displaying, need this to test zoom.
    viewer = imviz_helper.default_viewer._obj
    viewer.shape = (100, 100)
    viewer.state._set_axes_aspect_ratio(1)

    sky = SkyCoord(ra=[337.5202807, 337.51909197, 337.51760596],
                   dec=[-20.83305528, -20.83222194, -20.83083304], unit='deg')
    tbl = QTable({'sky_centroid': sky})  # Table has no "Label" column
    n_entries = len(tbl)

    ndd = NDData(np.ones((10, 10)), wcs=image_2d_wcs)
    imviz_helper.load_data(ndd, data_label='data_with_wcs')
    assert len(imviz_helper.app.data_collection) == 1

    catalogs_plugin = imviz_helper.plugins['Catalog Search']
    catalogs_plugin.import_catalog(tbl)
    out_tbl = catalogs_plugin._obj.search(error_on_fail=True)
    assert len(out_tbl) == n_entries
    assert catalogs_plugin._obj.number_of_results == n_entries
    # Assert that Object ID is set to index + 1 when the label column is absent
    for idx, item in enumerate(catalogs_plugin._obj.table.items):
        assert item['Object ID'] == str(idx + 1)
    assert len(imviz_helper.app.data_collection) == 2  # image + markers

    catalogs_plugin._obj.table.selected_rows = [catalogs_plugin._obj.table.items[0]]
    assert len(catalogs_plugin._obj.table.selected_rows) == 1

    # test to ensure sources searched for respect the maximum sources traitlet
    catalogs_plugin._obj.max_sources = 1
    catalogs_plugin._obj.search(error_on_fail=True)
    assert catalogs_plugin._obj.number_of_results == catalogs_plugin._obj.max_sources

    catalogs_plugin.clear_table()

    # test single source edge case and docs recommended input file type
    sky_coord = SkyCoord(ra=337.5202807, dec=-20.83305528, unit='deg')
    tbl = Table({'sky_centroid': [sky_coord], 'label': ['Source_1']})
    n_entries = len(tbl)

    catalogs_plugin.import_catalog(tbl)
    out_tbl = catalogs_plugin._obj.search()
    assert len([out_tbl]) == n_entries
    assert catalogs_plugin._obj.number_of_results == n_entries
    assert len(imviz_helper.app.data_collection) == 2  # image + markers

    catalogs_plugin.clear_table()
    assert not catalogs_plugin._obj.results_available
    assert len(imviz_helper.app.data_collection) == 1  # markers gone for good

    assert imviz_helper.viewers['imviz-0']._obj.state.x_min == -0.5
    assert imviz_helper.viewers['imviz-0']._obj.state.x_max == 9.5
    assert imviz_helper.viewers['imviz-0']._obj.state.y_min == -0.5
    assert imviz_helper.viewers['imviz-0']._obj.state.y_max == 9.5
    # Re-populate the table with a new search
    out_tbl = catalogs_plugin._obj.search()
    assert len(out_tbl) > 0
    # Ensure at least one row is selected before zooming
    catalogs_plugin._obj.table.selected_rows = [catalogs_plugin._obj.table.items[0]]
    assert len(catalogs_plugin._obj.table.selected_rows) > 0

    # test the zooming using the default 'padding' of 2% of the viewer size
    # around selected points
    catalogs_plugin.zoom_to_selected()
    assert_allclose(imviz_helper.viewers['imviz-0']._obj.state.x_min, -0.01966, rtol=1e-4)
    assert_allclose(imviz_helper.viewers['imviz-0']._obj.state.x_max, 0.02034, rtol=1e-4)
    assert_allclose(imviz_helper.viewers['imviz-0']._obj.state.y_min, 0.980008, rtol=1e-4)
    assert_allclose(imviz_helper.viewers['imviz-0']._obj.state.y_max, 1.020008, rtol=1e-4)


def test_zoom_to_selected(imviz_helper, image_2d_wcs):
    # Since we are not really displaying, need this to test zoom.
    viewer = imviz_helper.default_viewer._obj
    viewer.shape = (100, 100)
    viewer.state._set_axes_aspect_ratio(1)

    arr = np.ones((500, 500))
    ndd = NDData(arr, wcs=image_2d_wcs)
    imviz_helper.load_data(ndd)

    # sources at pixel coords ~(100, 100), ~(200, 200)
    sky_coord = SkyCoord(ra=[337.49056532, 337.46086081],
                         dec=[-20.80555273, -20.7777673], unit='deg')
    tbl = Table({'sky_centroid': [sky_coord],
                 'label': ['Source_1', 'Source_2']})

    catalogs_plugin = imviz_helper.plugins['Catalog Search']
    catalogs_plugin.import_catalog(tbl)
    catalogs_plugin._obj.search()

    # select both sources
    catalogs_plugin.select_all()

    # check viewer limits before zoom
    xmin, xmax, ymin, ymax = imviz_helper.default_viewer._obj.get_limits()
    assert xmin == ymin == -0.5
    assert xmax == ymax == 499.5

    # zoom to selected sources
    catalogs_plugin.zoom_to_selected()

    # make sure the viewer bounds reflect the zoom, which, in pixel coords,
    # should be centered at roughly pixel coords (150, 150)
    xmin, xmax, ymin, ymax = imviz_helper.default_viewer._obj.get_limits()

    assert_allclose((xmin + xmax) / 2, 150., atol=0.1)
    assert_allclose((ymin + ymax) / 2, 150., atol=0.1)

    # and the zoom box size should reflect the default padding of 2% of the image
    # size around the bounding box containing the source(s), which in this case is
    # 10 pixels around
    assert_allclose(xmin, 96, atol=0.1)  # min x of selected sources minus pad
    assert_allclose(xmax, 204, atol=0.1)  # max x of selected sources plus pad
    assert_allclose(ymin, 96, atol=0.1)  # min y of selected sources minus pad
    assert_allclose(ymax, 204, atol=0.1)  # max y of selected sources plus pad

    # select one source now
    catalogs_plugin._obj.table.selected_rows = catalogs_plugin._obj.table.items[0:1]

    # zoom to single selected source, using a new value for 'padding'
    catalogs_plugin.zoom_to_selected(padding=0.05)

    # check that zoom window is centered correctly on the source at 100, 100
    xmin, xmax, ymin, ymax = imviz_helper.default_viewer._obj.get_limits()
    assert_allclose((xmin + xmax) / 2, 100., atol=0.1)
    assert_allclose((ymin + ymax) / 2, 100., atol=0.1)

    # and the zoom box size should reflect the default padding of 5% of the image
    # size around the bounding box containing the source(s), which in this case is
    # 25 pixels around
    assert_allclose(xmin, 95, atol=0.1)  # min x of selected source minus pad
    assert_allclose(xmax, 105, atol=0.1)  # max x of selected source plus pad
    assert_allclose(ymin, 95, atol=0.1)  # min y of selected source minus pad
    assert_allclose(ymax, 105, atol=0.1)  # max y of selected source plus pad

    # test that appropriate error is raised when padding is not a valud percentage
    with pytest.raises(ValueError, match="padding must be between 0 .* and 1.*"):
        catalogs_plugin.zoom_to_selected(padding=5)


def test_select_tool(imviz_helper, image_2d_wcs):
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

    catalogs_plugin = imviz_helper.plugins['Catalog Search']
    catalogs_plugin.import_catalog(tbl)

    # before catalog searching, the selection tool is not available
    toolbar = imviz_helper.viewers['imviz-0']._obj.toolbar
    tool = toolbar.tools['jdaviz:selectcatalog']
    mark = catalogs_plugin._obj._get_mark(imviz_helper.viewers['imviz-0']._obj)
    assert tool.is_visible() is False

    catalogs_plugin._obj.search(error_on_fail=True)
    assert tool.is_visible()

    assert len(catalogs_plugin._obj.table.selected_rows) == 0
    assert len(catalogs_plugin._obj.table_selected.items) == 0
    assert len(mark.x) == 0

    toolbar.active_tool_id = 'jdaviz:selectcatalog'
    tool.on_mouse_event({'domain': {'x': 100, 'y': 110}})

    assert len(catalogs_plugin._obj.table.selected_rows) == 1
    assert len(catalogs_plugin._obj.table_selected.items) == 1
    assert len(mark.x) == 1

    tool.on_mouse_event({'domain': {'x': 200, 'y': 210}})
    assert len(catalogs_plugin._obj.table.selected_rows) == 2
    assert len(catalogs_plugin._obj.table_selected.items) == 2
    assert len(mark.x) == 2

    # click to remove
    tool.on_mouse_event({'domain': {'x': 110, 'y': 110}})
    assert len(catalogs_plugin._obj.table.selected_rows) == 1
    assert len(catalogs_plugin._obj.table_selected.items) == 1
    assert len(mark.x) == 1

    catalogs_plugin._obj.table_selected.clear_table()
    assert len(catalogs_plugin._obj.table.selected_rows) == 0
    assert len(catalogs_plugin._obj.table_selected.items) == 0
    assert len(mark.x) == 0


def test_offline_ecsv_catalog_with_extra_columns(imviz_helper, image_2d_wcs):
    # Create a table with additional columns
    sky = SkyCoord(ra=[337.5202807, 337.51909197, 337.51760596],
                   dec=[-20.83305528, -20.83222194, -20.83083304], unit='deg')
    tbl = QTable({
        'sky_centroid': sky,
        'flux': [1.0, 2.0, 3.0],
        'flux_err': [0.1, 0.2, 0.3],
        'is_extended': [False, True, False],
        'roundness': [0.01, 0.02, 0.03],
        'sharpness': [0.1, 0.2, 0.3]
    })

    ndd = NDData(np.ones((10, 10)), wcs=image_2d_wcs)
    imviz_helper.load_data(ndd, data_label='data_with_wcs')
    assert len(imviz_helper.app.data_collection) == 1

    catalogs_plugin = imviz_helper.plugins['Catalog Search']._obj
    catalogs_plugin.import_catalog(tbl)
    catalogs_plugin.search(error_on_fail=True)

    extra_columns = ['flux', 'flux_err', 'is_extended', 'roundness', 'sharpness']
    for col in extra_columns:
        assert col in catalogs_plugin.table.headers_avail

    # Check if extra columns are populated correctly
    for idx, item in enumerate(catalogs_plugin.table.items):
        assert float(item['flux']) == tbl['flux'][idx]
        assert float(item['flux_err']) == tbl['flux_err'][idx]
        assert item['is_extended'] == tbl['is_extended'][idx]
        assert float(item['roundness']) == tbl['roundness'][idx]
        assert float(item['sharpness']) == tbl['sharpness'][idx]


def test_select_catalog_table_rows(imviz_helper, image_2d_wcs):
    """Test the ``select_rows`` functionality on table in plugin."""

    arr = np.ones((500, 500))
    ndd = NDData(arr, wcs=image_2d_wcs)
    imviz_helper.load_data(ndd)

    sky_coord = SkyCoord(ra=[337.49, 337.46, 337.47, 337.48, 337.49, 337.50],
                         dec=[-20.81, -20.78, -20.79, -20.80, -20.77, -20.76],
                         unit='deg')
    tbl = Table({'sky_centroid': [sky_coord],
                'label': ['Source_1', 'Source_2', 'Source_3', 'Source_4',
                          'Source_5', 'Source_6']})

    catalogs_plugin = imviz_helper.plugins['Catalog Search']
    plugin_table = catalogs_plugin._obj.table

    # load catalog
    catalogs_plugin.import_catalog(tbl)
    catalogs_plugin._obj.search()

    # select a single row:
    catalogs_plugin.select_rows(3)
    assert len(plugin_table.selected_rows) == 1
    assert plugin_table.selected_rows[0]['Right Ascension (degrees)'] == '337.48000'

    # select multiple rows by indices
    catalogs_plugin.select_rows([3, 2, 4])
    assert len(plugin_table.selected_rows) == 3
    assert plugin_table.selected_rows[0]['Right Ascension (degrees)'] == '337.48000'
    assert plugin_table.selected_rows[1]['Right Ascension (degrees)'] == '337.47000'
    assert plugin_table.selected_rows[2]['Right Ascension (degrees)'] == '337.49000'

    # select a range of rows with a slice
    catalogs_plugin.select_rows(slice(0, 2))
    assert len(plugin_table.selected_rows) == 2
    assert plugin_table.selected_rows[0]['Right Ascension (degrees)'] == '337.49000'
    assert plugin_table.selected_rows[1]['Right Ascension (degrees)'] == '337.46000'

    # select rows with multi dim. numpy slice
    catalogs_plugin.select_rows(np.s_[0:2, 3:5])
    assert len(plugin_table.selected_rows) == 4
    assert plugin_table.selected_rows[0]['Right Ascension (degrees)'] == '337.49000'
    assert plugin_table.selected_rows[1]['Right Ascension (degrees)'] == '337.46000'
    assert plugin_table.selected_rows[2]['Right Ascension (degrees)'] == '337.48000'
    assert plugin_table.selected_rows[3]['Right Ascension (degrees)'] == '337.49000'

    # test select_all
    catalogs_plugin.select_all()
    assert len(plugin_table.selected_rows) == 6

    # test select_none
    catalogs_plugin.select_none()
    assert len(plugin_table.selected_rows) == 0
