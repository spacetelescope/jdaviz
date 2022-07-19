import numpy as np
import pytest
from astropy import units as u
from astropy.io import fits
from astropy.wcs import WCS
from specutils import Spectrum1D
from glue.core.roi import XRangeROI
from numpy.testing import assert_allclose

from jdaviz.utils import PRIHDR_KEY


@pytest.fixture
def image_hdu_obj():
    flux_hdu = fits.ImageHDU(np.ones((10, 10, 10)))
    flux_hdu.name = 'FLUX'

    mask_hdu = fits.ImageHDU(np.zeros((10, 10, 10)))
    mask_hdu.name = 'MASK'

    uncert_hdu = fits.ImageHDU(np.ones((10, 10, 10)))
    uncert_hdu.name = 'ERR'

    wcs = {
        'WCSAXES': 3, 'CRPIX1': 38.0, 'CRPIX2': 38.0, 'CRPIX3': 1.0,
        'PC1_1 ': -0.000138889, 'PC2_2 ': 0.000138889,
        'PC3_3 ': 8.33903304339E-11, 'CDELT1': 1.0, 'CDELT2': 1.0,
        'CDELT3': 1.0, 'CUNIT1': 'deg', 'CUNIT2': 'deg', 'CUNIT3': 'm',
        'CTYPE1': 'RA---TAN', 'CTYPE2': 'DEC--TAN', 'CTYPE3': 'WAVE-LOG',
        'CRVAL1': 205.4384, 'CRVAL2': 27.004754, 'CRVAL3': 3.62159598486E-07,
        'LONPOLE': 180.0, 'LATPOLE': 27.004754, 'MJDREFI': 0.0,
        'MJDREFF': 0.0, 'DATE-OBS': '2014-03-30',
        'RADESYS': 'FK5', 'EQUINOX': 2000.0
    }

    flux_hdu.header.update(wcs)
    flux_hdu.header['BUNIT'] = '1E-17 erg*s^-1*cm^-2*Angstrom^-1'

    uncert_hdu.header['BUNIT'] = '1E-17 erg*s^-1*cm^-2*Angstrom^-1'

    return fits.HDUList([fits.PrimaryHDU(), flux_hdu, uncert_hdu, mask_hdu])


@pytest.fixture
def image_hdu_obj_microns():
    flux_hdu = fits.ImageHDU(np.ones((8, 9, 10)).astype(np.float32))
    flux_hdu.name = 'FLUX'

    uncert_hdu = fits.ImageHDU(np.zeros((8, 9, 10)).astype(np.float32))
    uncert_hdu.name = 'ERR'

    mask_hdu = fits.ImageHDU(np.ones((8, 9, 10)).astype(np.uint16))
    mask_hdu.name = 'MASK'

    wcs = {
        'WCSAXES': 3, 'CRPIX1': 38.0, 'CRPIX2': 38.0, 'CRPIX3': 1.0,
        'CRVAL1': 205.4384, 'CRVAL2': 27.004754, 'CRVAL3': 4.890499866509344,
        'CTYPE1': 'RA---TAN', 'CTYPE2': 'DEC--TAN', 'CTYPE3': 'WAVE',
        'CUNIT1': 'deg', 'CUNIT2': 'deg', 'CUNIT3': 'um',
        'CDELT1': 3.61111097865634E-05, 'CDELT2': 3.61111097865634E-05, 'CDELT3': 0.001000000047497451,  # noqa
        'PC1_1 ': -1.0, 'PC1_2 ': 0.0, 'PC1_3 ': 0,
        'PC2_1 ': 0.0, 'PC2_2 ': 1.0, 'PC2_3 ': 0,
        'PC3_1 ': 0, 'PC3_2 ': 0, 'PC3_3 ': 1,
        'DISPAXIS': 2, 'VELOSYS': -2538.02,
        'SPECSYS': 'BARYCENT', 'RADESYS': 'ICRS', 'EQUINOX': 2000.0,
        'LONPOLE': 180.0, 'LATPOLE': 27.004754,
        'MJDREFI': 0.0, 'MJDREFF': 0.0, 'DATE-OBS': '2014-03-30'}

    flux_hdu.header.update(wcs)
    flux_hdu.header['BUNIT'] = '1E-17 erg*s^-1*cm^-2*Angstrom^-1'

    uncert_hdu.header['BUNIT'] = '1E-17 erg*s^-1*cm^-2*Angstrom^-1'

    return fits.HDUList([fits.PrimaryHDU(), flux_hdu, uncert_hdu, mask_hdu])


@pytest.mark.filterwarnings('ignore')
def test_fits_image_hdu_parse(image_hdu_obj, cubeviz_helper):
    cubeviz_helper.load_data(image_hdu_obj)

    assert len(cubeviz_helper.app.data_collection) == 3
    assert cubeviz_helper.app.data_collection[0].label.endswith('[FLUX]')


@pytest.mark.filterwarnings('ignore')
def test_fits_image_hdu_with_microns(image_hdu_obj_microns, cubeviz_helper):
    cubeviz_helper.load_data(image_hdu_obj_microns, data_label='has_microns')

    assert len(cubeviz_helper.app.data_collection) == 3
    assert cubeviz_helper.app.data_collection[0].label.endswith('[FLUX]')

    flux_cube = cubeviz_helper.app.data_collection[0].get_object(Spectrum1D, statistic=None)
    assert flux_cube.spectral_axis.unit == u.um

    # This tests the same data as test_fits_image_hdu_parse above.

    cubeviz_helper.app.data_collection[0].meta['EXTNAME'] == 'FLUX'
    cubeviz_helper.app.data_collection[1].meta['EXTNAME'] == 'MASK'
    cubeviz_helper.app.data_collection[2].meta['EXTNAME'] == 'ERR'
    for i in range(3):
        assert cubeviz_helper.app.data_collection[i].meta[PRIHDR_KEY]['BITPIX'] == 8

    flux_viewer = cubeviz_helper.app.get_viewer('flux-viewer')
    flux_viewer.on_mouse_or_key_event({'event': 'mousemove', 'domain': {'x': 0, 'y': 0}})
    assert flux_viewer.label_mouseover.pixel == 'x=00.0 y=00.0'
    assert flux_viewer.label_mouseover.value == '+1.00000e+00 1e-17 erg / (Angstrom cm2 s)'

    unc_viewer = cubeviz_helper.app.get_viewer('uncert-viewer')
    unc_viewer.on_mouse_or_key_event({'event': 'mousemove', 'domain': {'x': -1, 'y': 0}})
    assert unc_viewer.label_mouseover.pixel == 'x=-1.0 y=00.0'
    assert unc_viewer.label_mouseover.value == ''  # Out of bounds

    mask_viewer = cubeviz_helper.app.get_viewer('mask-viewer')
    mask_viewer.on_mouse_or_key_event({'event': 'mousemove', 'domain': {'x': 9, 'y': 0}})
    assert mask_viewer.label_mouseover.pixel == 'x=09.0 y=00.0'
    assert mask_viewer.label_mouseover.value == '+1.00000e+00 '  # Mask should be unitless


def test_spectrum1d_with_fake_fixed_units(spectrum1d, cubeviz_helper):
    header = {
        'WCSAXES': 1,
        'CRPIX1': 0.0,
        'CDELT1': 1E-06,
        'CUNIT1': 'm',
        'CTYPE1': 'WAVE',
        'CRVAL1': 0.0,
        'RADESYS': 'ICRS'}
    wcs = WCS(header)
    cubeviz_helper.app.add_data(spectrum1d, "test")

    dc = cubeviz_helper.app.data_collection
    dc[0].meta["_orig_wcs"] = wcs
    dc[0].meta["_orig_spec"] = spectrum1d

    cubeviz_helper.app.add_data_to_viewer('spectrum-viewer', 'test')
    cubeviz_helper.app.get_viewer('spectrum-viewer').apply_roi(XRangeROI(6600, 7400))

    subsets = cubeviz_helper.app.get_subsets_from_viewer("spectrum-viewer")
    reg = subsets.get('Subset 1')

    assert len(subsets) == 1
    assert_allclose(reg.lower.value, 6666.666666666667)
    assert_allclose(reg.upper.value, 7333.333333333334)
    assert reg.lower.unit == 'Angstrom'
    assert reg.upper.unit == 'Angstrom'


@pytest.mark.filterwarnings('ignore')
def test_fits_image_hdu_parse_from_file(tmpdir, image_hdu_obj, cubeviz_helper):
    f = tmpdir.join("test_fits_image.fits")
    path = f.strpath
    image_hdu_obj.writeto(path, overwrite=True)
    cubeviz_helper.load_data(path)

    assert len(cubeviz_helper.app.data_collection) == 3
    assert cubeviz_helper.app.data_collection[0].label.endswith('[FLUX]')

    # This tests the same data as test_fits_image_hdu_parse above.

    cubeviz_helper.app.data_collection[0].meta['EXTNAME'] == 'FLUX'
    cubeviz_helper.app.data_collection[1].meta['EXTNAME'] == 'MASK'
    cubeviz_helper.app.data_collection[2].meta['EXTNAME'] == 'ERR'
    for i in range(3):
        assert cubeviz_helper.app.data_collection[i].meta[PRIHDR_KEY]['BITPIX'] == 8

    flux_viewer = cubeviz_helper.app.get_viewer('flux-viewer')
    flux_viewer.on_mouse_or_key_event({'event': 'mousemove', 'domain': {'x': 0, 'y': 0}})
    assert flux_viewer.label_mouseover.pixel == 'x=00.0 y=00.0'
    assert flux_viewer.label_mouseover.value == '+1.00000e+00 1e-17 erg / (Angstrom cm2 s)'
    assert flux_viewer.label_mouseover.world_ra_deg == '205.4433848390'
    assert flux_viewer.label_mouseover.world_dec_deg == '26.9996149270'

    unc_viewer = cubeviz_helper.app.get_viewer('uncert-viewer')
    unc_viewer.on_mouse_or_key_event({'event': 'mousemove', 'domain': {'x': -1, 'y': 0}})
    assert unc_viewer.label_mouseover.pixel == 'x=-1.0 y=00.0'
    assert unc_viewer.label_mouseover.value == ''  # Out of bounds
    assert unc_viewer.label_mouseover.world_ra_deg == '205.4441642302'
    assert unc_viewer.label_mouseover.world_dec_deg == '26.9996148973'

    mask_viewer = cubeviz_helper.app.get_viewer('mask-viewer')
    mask_viewer.on_mouse_or_key_event({'event': 'mousemove', 'domain': {'x': 9, 'y': 0}})
    assert mask_viewer.label_mouseover.pixel == 'x=09.0 y=00.0'
    assert mask_viewer.label_mouseover.value == '+0.00000e+00 '  # Mask should be unitless
    assert mask_viewer.label_mouseover.world_ra_deg == '205.4441642302'
    assert mask_viewer.label_mouseover.world_dec_deg == '26.9996148973'


@pytest.mark.filterwarnings('ignore')
def test_spectrum3d_parse(image_hdu_obj, cubeviz_helper):
    flux = image_hdu_obj[1].data << u.Unit(image_hdu_obj[1].header['BUNIT'])
    wcs = WCS(image_hdu_obj[1].header, image_hdu_obj)
    sc = Spectrum1D(flux=flux, wcs=wcs)
    cubeviz_helper.load_data(sc)

    assert len(cubeviz_helper.app.data_collection) == 1
    assert cubeviz_helper.app.data_collection[0].label.endswith('[FLUX]')

    # Same as flux viewer data in test_fits_image_hdu_parse_from_file
    flux_viewer = cubeviz_helper.app.get_viewer('flux-viewer')
    flux_viewer.on_mouse_or_key_event({'event': 'mousemove', 'domain': {'x': 0, 'y': 0}})
    assert flux_viewer.label_mouseover.pixel == 'x=00.0 y=00.0'
    assert flux_viewer.label_mouseover.value == '+1.00000e+00 1e-17 erg / (Angstrom cm2 s)'
    assert flux_viewer.label_mouseover.world_ra_deg == '205.4433848390'
    assert flux_viewer.label_mouseover.world_dec_deg == '26.9996149270'

    # These viewers have no data.

    unc_viewer = cubeviz_helper.app.get_viewer('uncert-viewer')
    unc_viewer.on_mouse_or_key_event({'event': 'mousemove', 'domain': {'x': -1, 'y': 0}})
    assert unc_viewer.label_mouseover is None

    mask_viewer = cubeviz_helper.app.get_viewer('mask-viewer')
    mask_viewer.on_mouse_or_key_event({'event': 'mousemove', 'domain': {'x': 9, 'y': 0}})
    assert mask_viewer.label_mouseover is None


def test_spectrum1d_parse(spectrum1d, cubeviz_helper):
    cubeviz_helper.load_data(spectrum1d)

    assert len(cubeviz_helper.app.data_collection) == 1
    assert cubeviz_helper.app.data_collection[0].label.endswith('[FLUX]')
    assert cubeviz_helper.app.data_collection[0].meta['uncertainty_type'] == 'std'

    # Coordinate display is only for spatial image, which is missing here.
    flux_viewer = cubeviz_helper.app.get_viewer('flux-viewer')
    assert flux_viewer.label_mouseover is None


def test_numpy_cube(cubeviz_helper):
    with pytest.raises(NotImplementedError, match='Unsupported data format'):
        cubeviz_helper.load_data(np.ones(27).reshape((3, 3, 3)))


def test_multiple_load(image_hdu_obj, cubeviz_helper):
    cubeviz_helper.load_data(image_hdu_obj)

    # first load should be succesful; subsequent attempts should fail
    with pytest.raises(RuntimeError, match=r".?only one (data)?cube.?"):
        cubeviz_helper.load_data(image_hdu_obj)
