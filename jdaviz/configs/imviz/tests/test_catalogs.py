import pytest #not sure if I need this

import numpy as np

from astropy.io import fits

'''
Add commentary about what I'm currently testing, how to potentially improve the testing in the future, and what files I
used for testing. 
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

# testing that every variable updates accordingly when the image/data provided does not have any results
# leave breadcrumb of data used*
class TestCatalogs_NoResults():

    def test_plugin(self, imviz_helper):
        arr = np.ones((2048, 4096))

        # First data with WCS, same as the one in BaseImviz_WCS_NoWCS.
        hdu1 = fits.ImageHDU(arr, name='SCI')
        hdu1.header.update({'CTYPE1': 'RA---TAN-SIP',
                            'CUNIT1': 'deg',
                            'CDELT1': 0.01,
                            'CRPIX1': 2048.0,
                            'CRVAL1': 6.0705364649855,
                            'NAXIS1': 4096,
                            'CTYPE2': 'DEC--TAN-SIP',
                            'CUNIT2': 'deg',
                            'CDELT2': 0.01,
                            'CRPIX2': 1024.0,
                            'CRVAL2': -71.880349631403,
                            'NAXIS2': 2048})
        imviz_helper.load_data(hdu1, data_label='has_wcs')

        self.imviz = imviz_helper
        self.viewer = imviz_helper.default_viewer

        # Since we are not really displaying, need this to test zoom.
        self.viewer.shape = (475, 969)

        catalogs_plugin = self.imviz.app.get_tray_item_from_name('imviz-catalogs')
        catalogs_plugin.plugin_opened = True
        catalogs_plugin.vue_do_search()

        assert catalogs_plugin.results_available
        assert catalogs_plugin.number_of_results == 0

# testing that every variable updates accordingly when the image/data provided does have results
# leave breadcrumb of data used*
class TestCatalogs_Results():

    def test_plugin(self, imviz_helper):
        arr = np.ones((2048, 4096))

        # First data with WCS, same as the one in BaseImviz_WCS_NoWCS.
        hdu1 = fits.ImageHDU(arr, name='SCI')
        hdu1.header.update({'CTYPE1': 'RA---TAN',
                            'CUNIT1': 'deg',
                            'CDELT1': -0.00007063,
                            'CRPIX1': 1025.0,
                            'CRVAL1': 6.62750450757,
                            'NAXIS1': 2048,
                            'CTYPE2': 'DEC--TAN',
                            'CUNIT2': 'deg',
                            'CDELT2': 0.00007063,
                            'CRPIX2': 745.0,
                            'CRVAL2': 1.54470013629,
                            'NAXIS2': 1489})
        imviz_helper.load_data(hdu1, data_label='has_wcs')

        self.imviz = imviz_helper
        self.viewer = imviz_helper.default_viewer

        # Since we are not really displaying, need this to test zoom.
        self.viewer.shape = (475, 723)

        catalogs_plugin = self.imviz.app.get_tray_item_from_name('imviz-catalogs')
        catalogs_plugin.plugin_opened = True
        catalogs_plugin.vue_do_search()

        assert catalogs_plugin.results_available
        assert catalogs_plugin.number_of_results == 2473

        # testing that every variable updates accordingly when markers are cleared
        catalogs_plugin.vue_do_clear()

        assert not catalogs_plugin.results_available
