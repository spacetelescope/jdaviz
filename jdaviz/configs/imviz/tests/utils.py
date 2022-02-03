import numpy as np
import pytest
from astropy.io import fits
from astropy.wcs import WCS

__all__ = ['BaseImviz_WCS_NoWCS', 'BaseImviz_WCS_WCS']


class BaseImviz_WCS_NoWCS:
    @pytest.fixture(autouse=True)
    def setup_class(self, imviz_helper):
        hdu = fits.ImageHDU(np.arange(100).reshape((10, 10)), name='SCI')

        # Apply some celestial WCS from
        # https://learn.astropy.org/rst-tutorials/celestial_coords1.html
        hdu.header.update({'CTYPE1': 'RA---TAN',
                           'CUNIT1': 'deg',
                           'CDELT1': -0.0002777777778,
                           'CRPIX1': 1,
                           'CRVAL1': 337.5202808,
                           'NAXIS1': 10,
                           'CTYPE2': 'DEC--TAN',
                           'CUNIT2': 'deg',
                           'CDELT2': 0.0002777777778,
                           'CRPIX2': 1,
                           'CRVAL2': -20.833333059999998,
                           'NAXIS2': 10})

        # Data with WCS
        imviz_helper.load_data(hdu, data_label='has_wcs')

        # Data without WCS
        imviz_helper.load_data(hdu, data_label='no_wcs')
        imviz_helper.app.data_collection[1].coords = None

        self.wcs = WCS(hdu.header)
        self.imviz = imviz_helper
        self.viewer = imviz_helper.default_viewer

        # Since we are not really displaying, need this to test zoom.
        self.viewer.shape = (100, 100)
        self.viewer.state._set_axes_aspect_ratio(1)


class BaseImviz_WCS_WCS:
    @pytest.fixture(autouse=True)
    def setup_class(self, imviz_helper):
        arr = np.ones((10, 10))

        # First data with WCS, same as the one in BaseImviz_WCS_NoWCS.
        hdu1 = fits.ImageHDU(arr, name='SCI')
        hdu1.header.update({'CTYPE1': 'RA---TAN',
                            'CUNIT1': 'deg',
                            'CDELT1': -0.0002777777778,
                            'CRPIX1': 1,
                            'CRVAL1': 337.5202808,
                            'NAXIS1': 10,
                            'CTYPE2': 'DEC--TAN',
                            'CUNIT2': 'deg',
                            'CDELT2': 0.0002777777778,
                            'CRPIX2': 1,
                            'CRVAL2': -20.833333059999998,
                            'NAXIS2': 10})
        imviz_helper.load_data(hdu1, data_label='has_wcs_1')

        # Second data with WCS, similar to above but dithered by 1 pixel in X.
        # TODO: Use GWCS when https://github.com/spacetelescope/gwcs/issues/99 is possible.
        hdu2 = fits.ImageHDU(arr, name='SCI')
        hdu2.header.update({'CTYPE1': 'RA---TAN',
                            'CUNIT1': 'deg',
                            'CDELT1': -0.0002777777778,
                            'CRPIX1': 2,
                            'CRVAL1': 337.5202808,
                            'NAXIS1': 10,
                            'CTYPE2': 'DEC--TAN',
                            'CUNIT2': 'deg',
                            'CDELT2': 0.0002777777778,
                            'CRPIX2': 1,
                            'CRVAL2': -20.833333059999998,
                            'NAXIS2': 10})
        imviz_helper.load_data(hdu2, data_label='has_wcs_2')

        self.wcs_1 = WCS(hdu1.header)
        self.wcs_2 = WCS(hdu2.header)
        self.imviz = imviz_helper
        self.viewer = imviz_helper.default_viewer

        # Since we are not really displaying, need this to test zoom.
        self.viewer.shape = (100, 100)
        self.viewer.state._set_axes_aspect_ratio(1)
