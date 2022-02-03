import numpy as np
import pytest
from astropy import units as u
from astropy.io import fits
from astropy.wcs import WCS
from specutils import Spectrum1D


@pytest.fixture
def image_hdu_obj():
    flux_hdu = fits.ImageHDU(np.ones((10, 10, 10)))
    flux_hdu.name = 'FLUX'

    mask_hdu = fits.ImageHDU(np.zeros((10, 10, 10)))
    mask_hdu.name = 'MASK'

    uncert_hdu = fits.ImageHDU(np.ones((10, 10, 10)))
    uncert_hdu.name = 'ERR'

    wcs = WCS(header={
        'WCSAXES': 3, 'CRPIX1': 38.0, 'CRPIX2': 38.0, 'CRPIX3': 1.0,
        'PC1_1 ': -0.000138889, 'PC2_2 ': 0.000138889,
        'PC3_3 ': 8.33903304339E-11, 'CDELT1': 1.0, 'CDELT2': 1.0,
        'CDELT3': 1.0, 'CUNIT1': 'deg', 'CUNIT2': 'deg', 'CUNIT3': 'm',
        'CTYPE1': 'RA---TAN', 'CTYPE2': 'DEC--TAN', 'CTYPE3': 'WAVE-LOG',
        'CRVAL1': 205.4384, 'CRVAL2': 27.004754, 'CRVAL3': 3.62159598486E-07,
        'LONPOLE': 180.0, 'LATPOLE': 27.004754, 'MJDREFI': 0.0,
        'MJDREFF': 0.0, 'DATE-OBS': '2014-03-30',
        'RADESYS': 'FK5', 'EQUINOX': 2000.0
    })

    flux_hdu.header.update(wcs.to_header())
    flux_hdu.header['BUNIT'] = '1E-17 erg*s^-1*cm^-2*Angstrom^-1*pix^-1'

    mask_hdu.header.update(wcs.to_header())
    uncert_hdu.header.update(wcs.to_header())

    return fits.HDUList([fits.PrimaryHDU(), flux_hdu, mask_hdu, uncert_hdu])


@pytest.mark.filterwarnings('ignore')
def test_fits_image_hdu_parse(image_hdu_obj, cubeviz_helper):
    cubeviz_helper.load_data(image_hdu_obj)

    assert len(cubeviz_helper.app.data_collection) == 3
    assert cubeviz_helper.app.data_collection[0].label.endswith('[FLUX]')


@pytest.mark.filterwarnings('ignore')
def test_fits_image_hdu_parse_from_file(tmpdir, image_hdu_obj, cubeviz_helper):
    f = tmpdir.join("test_fits_image.fits")
    path = f.strpath
    image_hdu_obj.writeto(path, overwrite=True)
    cubeviz_helper.load_data(path)

    assert len(cubeviz_helper.app.data_collection) == 3
    assert cubeviz_helper.app.data_collection[0].label.endswith('[FLUX]')


@pytest.mark.filterwarnings('ignore')
def test_spectrum3d_parse(image_hdu_obj, cubeviz_helper):
    flux = image_hdu_obj[1].data << u.Unit(image_hdu_obj[1].header['BUNIT'])
    wcs = WCS(image_hdu_obj[1].header, image_hdu_obj)
    sc = Spectrum1D(flux=flux, wcs=wcs)
    cubeviz_helper.load_data(sc)

    assert len(cubeviz_helper.app.data_collection) == 1
    assert cubeviz_helper.app.data_collection[0].label.endswith('[FLUX]')


def test_spectrum1d_parse(spectrum1d, cubeviz_helper):
    cubeviz_helper.load_data(spectrum1d)

    assert len(cubeviz_helper.app.data_collection) == 1
    assert cubeviz_helper.app.data_collection[0].label.endswith('[FLUX]')


def test_numpy_cube(cubeviz_helper):
    with pytest.raises(NotImplementedError, match='Unsupported data format'):
        cubeviz_helper.load_data(np.ones(27).reshape((3, 3, 3)))
