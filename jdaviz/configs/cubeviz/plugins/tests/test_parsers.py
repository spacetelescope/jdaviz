import os

import astropy.units as u
import numpy as np
import pytest
from astropy.io import fits
from astropy.nddata import StdDevUncertainty
from astropy.wcs import WCS
from spectral_cube import SpectralCube
from specutils import Spectrum1D

from jdaviz.app import Application


@pytest.fixture
def cubeviz_app():
    return Application(configuration='cubeviz')


@pytest.fixture
def image_hdu_obj():
    flux_hdu = fits.ImageHDU(np.random.sample((10, 10, 10)))
    flux_hdu.name = 'FLUX'

    mask_hdu = fits.ImageHDU(np.zeros((10, 10, 10)))
    mask_hdu.name = 'MASK'

    uncert_hdu = fits.ImageHDU(np.random.sample((10, 10, 10)))
    uncert_hdu.name = 'ERR'

    wcs = WCS(header={
        'WCSAXES': 3, 'CRPIX1': 38.0, 'CRPIX2': 38.0, 'CRPIX3': 1.0,
        'PC1_1 ': -0.000138889, 'PC2_2 ': 0.000138889,
        'PC3_3 ': 8.33903304339E-11, 'CDELT1': 1.0, 'CDELT2': 1.0,
        'CDELT3': 1.0, 'CUNIT1': 'deg', 'CUNIT2': 'deg', 'CUNIT3': 'm',
        'CTYPE1': 'RA---TAN', 'CTYPE2': 'DEC--TAN', 'CTYPE3': 'WAVE-LOG',
        'CRVAL1': 205.4384, 'CRVAL2': 27.004754, 'CRVAL3': 3.62159598486E-07,
        'LONPOLE': 180.0, 'LATPOLE': 27.004754, 'MJDREFI': 0.0,
        'MJDREFF': 0.0, 'DATE-OBS': '2014-03-30', 'MJD-OBS': 56746.0,
        'RADESYS': 'FK5', 'EQUINOX': 2000.0
    })

    flux_hdu.header.update(wcs.to_header())
    flux_hdu.header['BUNIT'] = '1E-17 erg/s/cm^2/Angstrom/spaxel'

    mask_hdu.header.update(wcs.to_header())
    uncert_hdu.header.update(wcs.to_header())

    return fits.HDUList([fits.PrimaryHDU(), flux_hdu, mask_hdu, uncert_hdu])


def test_fits_image_hdu_parse(image_hdu_obj, cubeviz_app):
    cubeviz_app.load_data(image_hdu_obj)

    assert len(cubeviz_app.data_collection) == 3
    assert cubeviz_app.data_collection[0].label.endswith('[FLUX]')


def test_spectral_cube_parse(tmpdir, image_hdu_obj, cubeviz_app):
    f = tmpdir.join("test_fits_image.fits")
    path = os.path.join(f.dirname, f.basename)
    image_hdu_obj.writeto(path)

    sc = SpectralCube.read(path, hdu=1)

    cubeviz_app.load_data(sc)

    assert len(cubeviz_app.data_collection) == 1
    assert cubeviz_app.data_collection[0].label.endswith('[FLUX]')


def test_spectrum1d_parse(image_hdu_obj, cubeviz_app):
    spec = Spectrum1D(flux=np.random.sample(10) * u.Jy,
                      spectral_axis=np.arange(10) * u.nm,
                      uncertainty=StdDevUncertainty(
                          np.random.sample(10) * u.Jy))

    cubeviz_app.load_data(spec)

    assert len(cubeviz_app.data_collection) == 1
    assert cubeviz_app.data_collection[0].label.endswith('[FLUX]')
