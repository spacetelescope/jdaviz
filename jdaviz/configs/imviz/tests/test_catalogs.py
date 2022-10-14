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
import pytest

from astropy.io import fits
from astropy.nddata import NDData
from astropy.coordinates import SkyCoord
from astropy.table import QTable


@pytest.mark.remote_data
class TestCatalogs:

    # testing that the plugin search does not crash when no data/image is provided
    def test_plugin_no_image(self, imviz_helper):
        self.imviz = imviz_helper

        catalogs_plugin = self.imviz.app.get_tray_item_from_name('imviz-catalogs')
        catalogs_plugin.plugin_opened = True
        # running the search without any data loaded into Imviz
        catalogs_plugin.vue_do_search()

        assert not catalogs_plugin.results_available

    # testing that variables update correctly when the image/data provided does not have results
    def test_plugin_image_no_result(self, imviz_helper, image_2d_wcs):
        arr = np.ones((10, 10))
        ndd = NDData(arr, wcs=image_2d_wcs)

        imviz_helper.load_data(ndd, data_label='no_results_data')

        self.imviz = imviz_helper

        catalogs_plugin = self.imviz.app.get_tray_item_from_name('imviz-catalogs')
        catalogs_plugin.plugin_opened = True
        catalogs_plugin.vue_do_search()

        # number of results should be 0
        assert catalogs_plugin.results_available
        assert catalogs_plugin.number_of_results == 0

    # testing that every variable updates correctly when the image/data provided does have results
    # data used: information based on this image -
    # https://dr12.sdss.org/fields/runCamcolField?field=76&camcol=5&run=7674
    # the z-band FITS image was downloaded and used
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

        self.imviz = imviz_helper

        catalogs_plugin = self.imviz.app.get_tray_item_from_name('imviz-catalogs')
        catalogs_plugin.plugin_opened = True
        catalogs_plugin.vue_do_search()

        # number of results should be > 0
        # '2473' was determined by running the search with the image in the notebook
        assert catalogs_plugin.results_available
        assert catalogs_plugin.number_of_results == 2473

        # testing that every variable updates accordingly when markers are cleared
        catalogs_plugin.vue_do_clear()

        assert not catalogs_plugin.results_available

        # test loading from file
        table = imviz_helper.app._catalog_source_table
        skycoord_table = SkyCoord(table['ra'],
                                  table['dec'],
                                  unit='deg')
        qtable = QTable({'sky_centroid': skycoord_table})
        tmp_file = tmp_path / 'test.ecsv'
        qtable.write(tmp_file, overwrite=True)

        catalogs_plugin.from_file = str(tmp_file)
        # setting filename from API will automatically set catalog to 'From File...'
        assert catalogs_plugin.catalog.selected == 'From File...'
        catalogs_plugin.vue_do_search()
        assert catalogs_plugin.results_available
        assert catalogs_plugin.number_of_results == 2473


def test_from_file_parsing(imviz_helper, tmp_path):
    catalogs_plugin = imviz_helper.app.get_tray_item_from_name('imviz-catalogs')

    # _on_file_path_changed is fired when changing the selection in the file dialog
    catalogs_plugin._on_file_path_changed({'new': './invalid_path'})
    assert catalogs_plugin.from_file_message == 'File path does not exist'

    # observe('from_file') is fired when setting from_file from the API (or after clicking
    # select in the file dialog)
    with pytest.raises(ValueError, match='./invalid_path does not exist'):
        catalogs_plugin.from_file = './invalid_path'

    # setting to a blank string from the API resets the catalog selection to the
    # default/first entry
    catalogs_plugin.from_file = ''
    assert catalogs_plugin.catalog.selected == catalogs_plugin.catalog.choices[0]

    not_table_file = tmp_path / 'not_table.tst'
    not_table_file.touch()
    catalogs_plugin._on_file_path_changed({'new': not_table_file})
    assert catalogs_plugin.from_file_message == 'Could not parse file with astropy.table.QTable.read'  # noqa

    qtable = QTable({'not_sky_centroid': [1, 2, 3]})
    not_valid_table = tmp_path / 'not_valid_table.ecsv'
    qtable.write(not_valid_table, overwrite=True)
    catalogs_plugin._on_file_path_changed({'new': not_valid_table})
    assert catalogs_plugin.from_file_message == 'Table does not contain required sky_centroid column'  # noqa
