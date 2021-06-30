import numpy as np
import pytest
from astropy.io import fits
from astropy.wcs import WCS

__all__ = ['BaseImviz_WCS_NoWCS']


class BaseImviz_WCS_NoWCS:
    @pytest.fixture(autouse=True)
    def setup_class(self, imviz_app):
        hdu = fits.ImageHDU(np.zeros((10, 10)), name='SCI')

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
        imviz_app.load_data(hdu, data_label='has_wcs')

        # Data without WCS
        imviz_app.load_data(hdu, data_label='no_wcs')
        imviz_app.app.data_collection[1].coords = None

        self.wcs = WCS(hdu.header)
        self.imviz = imviz_app
        self.viewer = imviz_app.app.get_viewer('viewer-1')
