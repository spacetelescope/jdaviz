import numpy as np

from astropy.io import fits

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


# testing that the plugin search does not crash when no data/image is provided
class TestCatalogs_NoImage():

    def test_plugin(self, imviz_helper):
        self.imviz = imviz_helper

        catalogs_plugin = self.imviz.app.get_tray_item_from_name('imviz-catalogs')
        catalogs_plugin.plugin_opened = True
        # running the search without any data loaded into Imviz
        catalogs_plugin.vue_do_search()

        assert not catalogs_plugin.results_available


# testing that every variable updates correctly when the image/data provided does not have results
# data used: information based on the Imviz example notebook, variable "acs_47tuc_1"
# https://github.com/spacetelescope/jdaviz/blob/main/notebooks/ImvizExample.ipynb
class TestCatalogs_NoResults():

    def test_plugin(self, imviz_helper):
        arr = np.ones((2048, 4096))

        # header is based on the data provided above
        hdu1 = fits.ImageHDU(arr, name='SCI')
        hdu1.header.update({'CTYPE1': 'RA---TAN-SIP',
                            'CUNIT1': 'deg',
                            'CD1_1': 1.0548878548304e-05,
                            'CD1_2': 9.763832242379e-06,
                            'CRPIX1': 2048.0,
                            'CRVAL1': 6.0705364649855,
                            'NAXIS1': 4096,
                            'CTYPE2': 'DEC--TAN-SIP',
                            'CUNIT2': 'deg',
                            'CD2_1': 8.9680807000521e-06,
                            'CD2_2': -9.9965364544771e-06,
                            'CRPIX2': 1024.0,
                            'CRVAL2': -71.880349631403,
                            'NAXIS2': 2048})
        imviz_helper.load_data(hdu1, data_label='no_results_data')

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
class TestCatalogs_Results():

    def test_plugin(self, imviz_helper):
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
