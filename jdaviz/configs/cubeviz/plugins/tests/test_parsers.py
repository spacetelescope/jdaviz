from astropy.wcs import WCS
from astropy.io import fits
import numpy as np
import pytest
from jdaviz.app import Application


@pytest.fixture
def image_hdu_obj():
    hdu = fits.ImageHDU(np.zeros((10, 10, 10)))
    hdu.name = 'FLUX'
    wcs = WCS(header={
        'WCSAXES': 3, 'CRPIX1': 38.0, 'CRPIX2': 38.0, 'CRPIX3': 1.0,
        'PC1_1 ': -0.000138889, 'PC2_2 ': 0.000138889,
        'PC3_3 ': 8.33903304339E-11, 'CDELT1': 1.0, 'CDELT2': 1.0,
        'CDELT3': 1.0, 'CUNIT1': 'deg', 'CUNIT2': 'deg', 'CUNIT3': 'm',
        'CTYPE1': 'RA---TAN', 'CTYPE2': 'DEC--TAN', 'CTYPE3': 'WAVE-LOG',
        'CRVAL1': 205.4384, 'CRVAL2': 27.004754, 'CRVAL3': 3.62159598486E-07,
        'LONPOLE': 180.0, 'LATPOLE': 27.004754, 'MJDREFI': 0.0,
        'MJDREFF': 0.0, 'DATE-OBS': '2014-03-30', 'MJD-OBS': 56746.0,
        'MJD-OBS': 56746.0, 'RADESYS': 'FK5', 'EQUINOX': 2000.0
    })
    hdu.header.update(wcs.to_header())

    return fits.HDUList([fits.PrimaryHDU(), hdu])


@pytest.fixture
def spectral_cube_obj():
    return


def test_fits_image_hdu_parse(image_hdu_obj):
    app = Application(configuration='cubeviz')

    app.load_data(image_hdu_obj)


def test_spectral_cube_parse(spectral_cube_obj):

