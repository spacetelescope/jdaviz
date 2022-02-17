import numpy as np
import pytest
from astropy import units as u
from astropy.io import fits
from astropy.tests.helper import assert_quantity_allclose
from astropy.wcs import WCS
from glue_astronomy.translators.spectrum1d import PaddedSpectrumWCS
from numpy.testing import assert_array_equal, assert_allclose
from specutils import Spectrum1D

from jdaviz.configs.cubeviz.plugins.parsers import parse_data, _fix_jwst_s3d_sci_header


@pytest.fixture
def image_hdu_obj():
    flux_hdu = fits.ImageHDU(np.ones((5, 8, 10), dtype=np.float32))  # X=10 Y=10 WAVE=5
    flux_hdu.name = 'FLUX'

    uncert_hdu = fits.ImageHDU(np.ones((5, 8, 10), dtype=np.float32))
    uncert_hdu.name = 'ERR'

    mask_hdu = fits.ImageHDU(np.zeros((5, 8, 10), dtype=np.int32))
    mask_hdu.name = 'MASK'

    invalid_hdu_1 = fits.ImageHDU(np.zeros((2, 2), dtype=np.int16))
    invalid_hdu_1.name = 'WRONGDIM'

    invalid_hdu_2 = fits.ImageHDU(np.ones((5, 8, 10), dtype=np.float32))
    invalid_hdu_2.name = 'NOTCUBEVIZCUBE'

    wcs_header = {
        'WCSAXES': 3, 'CRPIX1': 38.0, 'CRPIX2': 38.0, 'CRPIX3': 1.0,
        'PC1_1 ': -0.000138889, 'PC2_2 ': 0.000138889,
        'PC3_3 ': 8.33903304339E-11, 'CDELT1': 1.0, 'CDELT2': 1.0,
        'CDELT3': 1.0, 'CUNIT1': 'deg', 'CUNIT2': 'deg', 'CUNIT3': 'm',
        'CTYPE1': 'RA---TAN', 'CTYPE2': 'DEC--TAN', 'CTYPE3': 'WAVE-LOG',
        'CRVAL1': 205.4384, 'CRVAL2': 27.004754, 'CRVAL3': 3.62159598486E-07,
        'LONPOLE': 180.0, 'LATPOLE': 27.004754, 'MJDREFI': 0.0,
        'MJDREFF': 0.0, 'DATE-OBS': '2014-03-30',
        'RADESYS': 'FK5', 'EQUINOX': 2000.0}

    flux_hdu.header.update(wcs_header)
    flux_hdu.header['BUNIT'] = '1E-17 erg*s^-1*cm^-2*Angstrom^-1*pix^-1'

    return fits.HDUList([fits.PrimaryHDU(), flux_hdu, uncert_hdu, mask_hdu,
                         invalid_hdu_1, invalid_hdu_2])


@pytest.mark.filterwarnings('ignore')
def test_fits_image_hdulist_parse(image_hdu_obj, cubeviz_helper):
    cubeviz_helper.load_data(image_hdu_obj, data_label='my_hdu')
    assert len(cubeviz_helper.app.data_collection) == 3

    data = cubeviz_helper.app.data_collection[0]
    flux = data.get_component('flux')
    data_unit = '1e-17 erg / (Angstrom cm2 pix s)'
    assert data.label == 'my_hdu[FLUX]'
    assert data.shape == (5, 8, 10)
    assert isinstance(data.coords, WCS)
    assert_array_equal(flux.data, 1)
    assert flux.units == data_unit

    # NOTE: ERR and MASK inherit WCS from FLUX when all passed in as HDUList.

    data = cubeviz_helper.app.data_collection[1]
    flux = data.get_component('flux')
    assert data.label == 'my_hdu[ERR]'
    assert data.shape == (5, 8, 10)
    assert isinstance(data.coords, WCS)  # Inherited
    assert_array_equal(flux.data, 1)
    assert flux.units == data_unit  # Inherited

    data = cubeviz_helper.app.data_collection[2]
    flux = data.get_component('flux')
    assert data.label == 'my_hdu[MASK]'
    assert data.shape == (5, 8, 10)
    assert isinstance(data.coords, WCS)   # Inherited
    assert_array_equal(flux.data, 0)
    assert flux.units == ''  # Mask should be unitless

    spec = cubeviz_helper.app.get_data_from_viewer('spectrum-viewer', 'my_hdu[FLUX]')
    assert_quantity_allclose(spec.flux, 1 * u.Unit(data_unit))
    assert_quantity_allclose(spec.spectral_axis.radial_velocity, 0 * (u.km / u.s))
    assert_quantity_allclose(spec.spectral_axis.redshift, 0)
    assert_quantity_allclose(spec.spectral_axis.si, [3.62159598e-07, 3.62242998e-07, 3.62326418e-07,
                                                     3.62409856e-07, 3.62493313e-07] * u.m)


@pytest.mark.filterwarnings('ignore')
def test_fits_image_hdu_parse(image_hdu_obj, cubeviz_helper):
    cubeviz_helper.load_data(image_hdu_obj['FLUX'], data_label='myhdu[left]')
    cubeviz_helper.load_data(image_hdu_obj['ERR'], data_label='myhdu[center]')
    cubeviz_helper.load_data(image_hdu_obj['MASK'], data_label='myhdu[right]')

    assert len(cubeviz_helper.app.data_collection) == 3

    data = cubeviz_helper.app.data_collection[0]
    flux = data.get_component('flux')
    data_unit = '1e-17 erg / (Angstrom cm2 pix s)'
    assert data.label == 'myhdu[left]'
    assert data.shape == (5, 8, 10)
    assert isinstance(data.coords, WCS)
    assert_array_equal(flux.data, 1)
    assert flux.units == data_unit

    data = cubeviz_helper.app.data_collection[1]
    flux = data.get_component('flux')
    assert data.label == 'myhdu[center]'
    assert data.shape == (5, 8, 10)
    assert isinstance(data.coords, PaddedSpectrumWCS)
    assert_array_equal(flux.data, 1)
    assert flux.units == 'ct'  # Fallback unit

    data = cubeviz_helper.app.data_collection[2]
    flux = data.get_component('flux')
    assert data.label == 'myhdu[right]'
    assert data.shape == (5, 8, 10)
    assert isinstance(data.coords, PaddedSpectrumWCS)
    assert_array_equal(flux.data, 0)
    assert flux.units == ''  # Mask should be unitless

    spec = cubeviz_helper.app.get_data_from_viewer('spectrum-viewer', 'myhdu[left]')
    assert_quantity_allclose(spec.flux, 1 * u.Unit(data_unit))
    assert_quantity_allclose(spec.spectral_axis.radial_velocity, 0 * (u.km / u.s))
    assert_quantity_allclose(spec.spectral_axis.redshift, 0)
    assert_quantity_allclose(spec.spectral_axis.si, [3.62159598e-07, 3.62242998e-07, 3.62326418e-07,
                                                     3.62409856e-07, 3.62493313e-07] * u.m)


def test_fits_image_hdu_parse_4d(cubeviz_helper):
    cubeviz_helper.load_data(fits.ImageHDU(np.ones(24).reshape((1, 2, 3, 4)), name='SCI'))

    assert len(cubeviz_helper.app.data_collection) == 1
    data = cubeviz_helper.app.data_collection[0]
    flux = data.get_component('flux')
    assert data.shape == (2, 3, 4)
    assert isinstance(data.coords, PaddedSpectrumWCS)
    assert_array_equal(flux.data, 1)
    assert flux.units == 'ct'

    with pytest.raises(ValueError, match='HDU is not supported as data cube'):
        cubeviz_helper.load_data(fits.ImageHDU(np.ones(48).reshape((2, 2, 3, 4)), name='SCI'))


@pytest.mark.filterwarnings('ignore')
def test_fits_image_hdulist_parse_from_file(tmpdir, image_hdu_obj, cubeviz_helper):
    path = tmpdir.join("test_fits_image.fits").strpath
    image_hdu_obj.writeto(path, overwrite=True)

    cubeviz_helper.load_data(path)
    assert len(cubeviz_helper.app.data_collection) == 3

    # Contents already tested in test_fits_image_hdulist_parse()
    assert cubeviz_helper.app.data_collection[0].label == 'test_fits_image.fits[FLUX]'
    assert cubeviz_helper.app.data_collection[1].label == 'test_fits_image.fits[ERR]'
    assert cubeviz_helper.app.data_collection[2].label == 'test_fits_image.fits[MASK]'


@pytest.mark.filterwarnings('ignore')
def test_spectrum3d_parse(spectrum1d_cube, cubeviz_helper):
    cubeviz_helper.load_data(spectrum1d_cube)
    assert len(cubeviz_helper.app.data_collection) == 3

    data = cubeviz_helper.app.data_collection[0]
    flux = data.get_component('flux')
    data_unit = 'Jy'
    wcs_ctypes = ['RA---TAN', 'DEC--TAN', 'WAVE-LOG']
    assert data.label.endswith('[FLUX]')
    assert data.shape == (2, 2, 4)
    assert list(data.coords.wcs.ctype) == wcs_ctypes
    assert flux.units == data_unit

    data = cubeviz_helper.app.data_collection[1]
    flux = data.get_component('flux')
    assert data.label.endswith('[UNCERTAINTY]')
    assert data.shape == (2, 2, 4)
    assert list(data.coords.wcs.ctype) == wcs_ctypes
    assert flux.units == data_unit

    data = cubeviz_helper.app.data_collection[2]
    flux = data.get_component('flux')
    assert data.label.endswith('[MASK]')
    assert data.shape == (2, 2, 4)
    assert list(data.coords.wcs.ctype) == wcs_ctypes
    assert flux.units == ''  # Mask should be unitless


def test_spectrum3d_no_wcs_parse(cubeviz_helper):
    sc = Spectrum1D(flux=np.ones(24).reshape((2, 3, 4)) * u.nJy)
    cubeviz_helper.load_data(sc)
    assert len(cubeviz_helper.app.data_collection) == 1
    assert sc.spectral_axis.unit == u.pix

    data = cubeviz_helper.app.data_collection[0]
    flux = data.get_component('flux')
    assert data.label.endswith('[FLUX]')
    assert data.shape == (2, 3, 4)
    assert isinstance(data.coords, PaddedSpectrumWCS)
    assert_array_equal(flux.data, 1)
    assert flux.units == 'nJy'


def test_spectrum1d_parse(spectrum1d, cubeviz_helper):
    cubeviz_helper.load_data(spectrum1d)
    assert len(cubeviz_helper.app.data_collection) == 1
    assert cubeviz_helper.app.data_collection[0].label.endswith('[FLUX]')


@pytest.mark.parametrize(('data_type', 'label_suffix', 'flux_unit'),
                         [(None, '[FLUX]', 'ct'),
                          ('uncert', '[UNCERT]', 'ct'),
                          ('mask', '[MASK]', '')])
def test_numpy_cube(cubeviz_helper, data_type, label_suffix, flux_unit):
    # spectral axis has length 2
    cubeviz_helper.load_data(np.ones(24).reshape((2, 3, 4)), data_type=data_type)
    assert len(cubeviz_helper.app.data_collection) == 1

    data = cubeviz_helper.app.data_collection[0]
    flux = data.get_component('flux')
    assert data.label.endswith(label_suffix)
    assert data.shape == (2, 3, 4)
    assert isinstance(data.coords, PaddedSpectrumWCS)
    assert flux.units == flux_unit


def test_numpy_cube_4d(cubeviz_helper):
    cubeviz_helper.load_data(np.ones(24).reshape((1, 2, 3, 4)))
    assert len(cubeviz_helper.app.data_collection) == 1

    data = cubeviz_helper.app.data_collection[0]
    flux = data.get_component('flux')
    assert data.label.endswith('[FLUX]')
    assert data.shape == (2, 3, 4)
    assert isinstance(data.coords, PaddedSpectrumWCS)
    assert flux.units == 'ct'

    with pytest.raises(NotImplementedError, match='Unsupported data format'):
        cubeviz_helper.load_data(np.ones(48).reshape((2, 2, 3, 4)))


def test_invalid_data_types(cubeviz_helper):
    with pytest.raises(FileNotFoundError, match='Could not locate file'):
        cubeviz_helper.load_data('foo')

    with pytest.raises(ValueError, match='data_type must be one of'):
        cubeviz_helper.load_data(np.ones((2, 2, 2)), data_type='bar')

    with pytest.raises(NotImplementedError, match='Unsupported data format'):
        cubeviz_helper.load_data(Spectrum1D(flux=np.ones((2, 2)) * u.nJy))

    with pytest.raises(NotImplementedError, match='Unsupported data format'):
        cubeviz_helper.load_data(np.ones((2, )))

    with pytest.raises(NotImplementedError, match='Unsupported data format'):
        cubeviz_helper.load_data(fits.TableHDU())

    # Lower level parsing logic.

    with pytest.raises(ValueError, match='HDU is not supported as data cube'):
        parse_data(cubeviz_helper.app, fits.PrimaryHDU(), 'flux')

    with pytest.raises(ValueError, match='Unsupported extname'):
        parse_data(cubeviz_helper.app, fits.ImageHDU(np.ones((2, 2, 2)), name='bar'))


@pytest.mark.parametrize(('date_key', 'date_val'),
                         [('MJD-BEG', 59573.0),
                          ('DATE-OBS', '2021-12-25')])
def test_fix_invalid_jwst_s3d_sci_header(date_key, date_val):
    extname = 'SCI'
    sci_hdu = fits.ImageHDU()
    sci_hdu.name = extname
    sci_hdu.header[date_key] = date_val
    hdu_list = fits.HDUList([sci_hdu])
    _fix_jwst_s3d_sci_header(hdu_list)
    assert_allclose(hdu_list[extname].header['MJD-OBS'], 59573)
