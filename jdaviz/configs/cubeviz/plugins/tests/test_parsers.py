import warnings

import numpy as np
import pytest
from astropy import units as u
from astropy.wcs import WCS
from gwcs.wcs import WCS as GWCS
from specutils import Spectrum, SpectralRegion
from numpy.testing import assert_allclose, assert_array_equal

from jdaviz.core.custom_units_and_equivs import PIX2
from jdaviz.utils import PRIHDR_KEY


@pytest.mark.filterwarnings('ignore')
def test_fits_image_hdu_parse(image_cube_hdu_obj, cubeviz_helper):
    cubeviz_helper.load_data(image_cube_hdu_obj)

    assert len(cubeviz_helper.app.data_collection) == 4  # 3 cubes and extracted spectrum
    assert cubeviz_helper.app.data_collection[0].label == "Unknown HDU object[FLUX]"

    # first load should be successful; subsequent attempts should fail
    with pytest.raises(RuntimeError, match="Only one cube"):
        cubeviz_helper.load_data(image_cube_hdu_obj)


@pytest.mark.filterwarnings('ignore')
def test_fits_image_hdu_with_microns(image_cube_hdu_obj_microns, cubeviz_helper):
    # Passing in data_label keyword as posarg.
    cubeviz_helper.load_data(image_cube_hdu_obj_microns, 'has_microns')

    assert len(cubeviz_helper.app.data_collection) == 4  # 3 cubes and extracted spectrum
    assert cubeviz_helper.app.data_collection[0].label == 'has_microns[FLUX]'

    flux_cube = cubeviz_helper.app.data_collection[0].get_object(Spectrum, statistic=None)
    assert flux_cube.spectral_axis.unit == u.um

    # This tests the same data as test_fits_image_hdu_parse above.
    cubeviz_helper.app.data_collection[0].meta['EXTNAME'] == 'FLUX'
    cubeviz_helper.app.data_collection[1].meta['EXTNAME'] == 'MASK'
    cubeviz_helper.app.data_collection[2].meta['EXTNAME'] == 'ERR'
    for i in range(3):
        assert cubeviz_helper.app.data_collection[i].meta[PRIHDR_KEY]['BITPIX'] == 8

    flux_viewer = cubeviz_helper.app.get_viewer('flux-viewer')
    label_mouseover = cubeviz_helper._coords_info
    label_mouseover._viewer_mouse_event(flux_viewer,
                                        {'event': 'mousemove', 'domain': {'x': 0, 'y': 0}})

    # This secondarily tests a scale factor embedded in a unit at parse-time to make sure it
    # is applied to the values, then it is removed from the actual display unit
    flux_unit_str = "erg / (Angstrom s cm2 pix2)"
    assert label_mouseover.as_text() == (f'Pixel x=00.0 y=00.0 Value +5.00000e-17 {flux_unit_str}',  # noqa
                                         'World 13h41m45.5759s +27d00m12.3044s (ICRS)',
                                         '205.4398995981 27.0034178810 (deg)')  # noqa

    # verify that scale factor embedded in unit is removed
    assert np.allclose(flux_cube.unit.scale, 1.0)

    unc_viewer = cubeviz_helper.app.get_viewer('uncert-viewer')
    label_mouseover._viewer_mouse_event(unc_viewer,
                                        {'event': 'mousemove', 'domain': {'x': -1, 'y': 0}})
    assert label_mouseover.as_text() == ('Pixel x=-1.0 y=00.0',  # Out of bounds
                                         'World 13h41m45.5856s +27d00m12.3044s (ICRS)',
                                         '205.4399401278 27.0034178806 (deg)')


def test_spectrum1d_with_fake_fixed_units(spectrum1d, cubeviz_helper):
    cubeviz_helper.app.add_data(spectrum1d, "test")

    dc = cubeviz_helper.app.data_collection
    dc[0].meta["_orig_spec"] = spectrum1d

    cubeviz_helper.app.add_data_to_viewer('spectrum-viewer', 'test')
    unit = u.Unit(cubeviz_helper.plugins['Unit Conversion'].spectral_unit.selected)
    cubeviz_helper.plugins['Subset Tools'].import_region(SpectralRegion(6600 * unit,
                                                                        7400 * unit))

    subsets = cubeviz_helper.app.get_subsets()
    reg = subsets.get('Subset 1')

    assert len(subsets) == 1
    assert_allclose(reg.lower.value, 6600.)
    assert_allclose(reg.upper.value, 7400.)
    assert reg.lower.unit == 'Angstrom'
    assert reg.upper.unit == 'Angstrom'


@pytest.mark.filterwarnings('ignore')
def test_fits_image_hdu_parse_from_file(tmpdir, image_cube_hdu_obj, cubeviz_helper):
    f = tmpdir.join("test_fits_image.fits")
    path = f.strpath
    image_cube_hdu_obj.writeto(path, overwrite=True)
    cubeviz_helper.load_data(path)

    assert len(cubeviz_helper.app.data_collection) == 4  # 3 cubes and auto-extracted spectrum
    assert cubeviz_helper.app.data_collection[0].label == "test_fits_image.fits[FLUX]"

    # This tests the same data as test_fits_image_hdu_parse above.
    cubeviz_helper.app.data_collection[0].meta['EXTNAME'] == 'FLUX'
    cubeviz_helper.app.data_collection[1].meta['EXTNAME'] == 'MASK'
    cubeviz_helper.app.data_collection[2].meta['EXTNAME'] == 'ERR'
    for i in range(3):
        assert cubeviz_helper.app.data_collection[i].meta[PRIHDR_KEY]['BITPIX'] == 8

    flux_viewer = cubeviz_helper.app.get_viewer(cubeviz_helper._default_flux_viewer_reference_name)
    label_mouseover = cubeviz_helper._coords_info
    label_mouseover._viewer_mouse_event(flux_viewer,
                                        {'event': 'mousemove', 'domain': {'x': 0, 'y': 0}})
    flux_unit_str = "erg / (Angstrom s cm2 pix2)"
    assert label_mouseover.as_text() == (f'Pixel x=00.0 y=00.0 Value +1.00000e-17 {flux_unit_str}',  # noqa
                                         'World 13h41m46.5994s +26d59m58.6136s (ICRS)',
                                         '205.4441642302 26.9996148973 (deg)')

    unc_viewer = cubeviz_helper.app.get_viewer(cubeviz_helper._default_uncert_viewer_reference_name)
    label_mouseover._viewer_mouse_event(unc_viewer,
                                        {'event': 'mousemove', 'domain': {'x': -1, 'y': 0}})
    assert label_mouseover.as_text() == ('Pixel x=-1.0 y=00.0',  # Out of bounds
                                         'World 13h41m46.6368s +26d59m58.6136s (ICRS)',
                                         '205.4443201084 26.9996148908 (deg)')


@pytest.mark.filterwarnings('ignore')
def test_spectrum3d_parse(image_cube_hdu_obj, cubeviz_helper):
    flux = image_cube_hdu_obj[1].data << u.Unit(image_cube_hdu_obj[1].header['BUNIT'])
    wcs = WCS(image_cube_hdu_obj[1].header, image_cube_hdu_obj)
    sc = Spectrum(flux=flux, wcs=wcs)
    cubeviz_helper.load_data(sc)

    data = cubeviz_helper.app.data_collection[0]
    assert len(cubeviz_helper.app.data_collection) == 2
    assert data.label == "Unknown spectrum object[FLUX]"
    assert data.shape == flux.shape

    # Same as flux viewer data in test_fits_image_hdu_parse_from_file
    flux_viewer = cubeviz_helper.app.get_viewer(cubeviz_helper._default_flux_viewer_reference_name)
    label_mouseover = cubeviz_helper._coords_info
    label_mouseover._viewer_mouse_event(flux_viewer,
                                        {'event': 'mousemove', 'domain': {'x': 0, 'y': 0}})
    flux_unit_str = "erg / (Angstrom s cm2 pix2)"
    assert label_mouseover.as_text() == (f'Pixel x=00.0 y=00.0 Value +1.00000e-17 {flux_unit_str}',  # noqa
                                         'World 13h41m46.5994s +26d59m58.6136s (ICRS)',
                                         '205.4441642302 26.9996148973 (deg)')

    # These viewers have no data.
    unc_viewer = cubeviz_helper.app.get_viewer(cubeviz_helper._default_uncert_viewer_reference_name)
    label_mouseover._viewer_mouse_event(unc_viewer,
                                        {'event': 'mousemove', 'domain': {'x': -1, 'y': 0}})
    assert label_mouseover.as_text() == ('', '', '')


@pytest.mark.parametrize("flux_unit", [u.nJy, u.DN, u.DN / u.s])
def test_spectrum3d_no_wcs_parse(cubeviz_helper, flux_unit):
    sc = Spectrum(flux=np.ones(24).reshape((2, 3, 4)) * flux_unit, spectral_axis_index=2)  # x, y, z
    cubeviz_helper.load_data(sc)
    assert sc.spectral_axis.unit == u.pix

    data = cubeviz_helper.app.data_collection[0]
    flux = data.get_component('flux')
    assert data.label.endswith('[FLUX]')
    assert data.shape == (2, 3, 4)  # x, y, z
    assert isinstance(data.coords, GWCS)
    assert_array_equal(flux.data, 1)
    assert flux.units == f'{flux_unit / PIX2}'


def test_spectrum1d_parse(spectrum1d, cubeviz_helper):
    cubeviz_helper.load_data(spectrum1d)

    assert len(cubeviz_helper.app.data_collection) == 1
    assert cubeviz_helper.app.data_collection[0].label.endswith('Spectrum')
    assert cubeviz_helper.app.data_collection[0].meta['uncertainty_type'] == 'std'

    # Coordinate display is only for spatial image, which is missing here.
    label_mouseover = cubeviz_helper._coords_info
    assert label_mouseover.as_text() == ('', '', '')


def test_numpy_cube(cubeviz_helper):
    arr = np.ones(24).reshape((4, 3, 2))  # x, y, z

    with pytest.raises(TypeError, match='Data type must be one of'):
        cubeviz_helper.load_data(arr, data_type='foo')

    cubeviz_helper.load_data(arr)
    cubeviz_helper.load_data(arr, data_label='uncert_array', data_type='uncert',
                             override_cube_limit=True)

    with pytest.raises(RuntimeError, match='Only one cube'):
        cubeviz_helper.load_data(arr, data_type='mask')

    assert len(cubeviz_helper.app.data_collection) == 3  # flux cube, uncert cube, Spectrum (sum)

    # Check context of first cube.
    data = cubeviz_helper.app.data_collection[0]
    flux = data.get_component('flux')
    assert data.label == 'Array'
    assert data.shape == (4, 3, 2)  # x, y, z
    assert isinstance(data.coords, GWCS)
    assert flux.units == 'ct / pix2'

    # Check context of second cube.
    data = cubeviz_helper.app.data_collection[1]
    flux = data.get_component('flux')
    assert data.label == 'uncert_array'
    assert data.shape == (4, 3, 2)  # x, y, z
    assert isinstance(data.coords, GWCS)
    assert flux.units == 'ct / pix2'


def test_loading_with_mask(cubeviz_helper):
    # This also tests that spaxel is converted to pix**2
    custom_spec = Spectrum(flux=[[[20, 1], [9, 1]], [[3, 1], [6, np.nan]]] * u.Unit("erg / Angstrom s cm**2 spaxel"),  # noqa
                           spectral_axis=[1, 2]*u.AA,
                           mask=[[[1, 0], [0, 0]], [[0, 0], [0, 0]]],
                           spectral_axis_index=2)
    cubeviz_helper.load_data(custom_spec)

    uc = cubeviz_helper.plugins['Unit Conversion']
    uc.spectral_y_type = "Surface Brightness"

    se = cubeviz_helper.plugins['3D Spectral Extraction']
    se.function = "Mean"
    se.extract()
    extracted = cubeviz_helper.get_data("Spectrum (mean)")
    assert_allclose(extracted.flux.value, [6, 1])
    assert extracted.unit == u.Unit("erg / Angstrom s cm**2 pix**2")


@pytest.mark.remote_data
@pytest.mark.parametrize(
    'function, expected_value,',
    (
        ('Mean', 5.566169e-18),
        ('Sum', 1.553518e-14),
        ('Max', 1e20),
    )
)
def test_manga_with_mask(cubeviz_helper, function, expected_value):
    # Remote data test of loading and extracting an up-to-date (as of 11/19/2024) MaNGA cube
    # This also tests that spaxel is converted to pix**2
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore")
        cubeviz_helper.load_data("https://stsci.box.com/shared/static/gts87zqt5265msuwi4w5u003b6typ6h0.gz", cache=True)  # noqa

    uc = cubeviz_helper.plugins['Unit Conversion']
    uc.spectral_y_type = "Surface Brightness"

    se = cubeviz_helper.plugins['3D Spectral Extraction']
    se.function = function
    se.extract()
    extracted_max = cubeviz_helper.get_data(f"Spectrum ({function.lower()})").max()
    assert_allclose(extracted_max.value, expected_value, rtol=5e-7)
    if function == "Sum":
        assert extracted_max.unit == u.Unit("erg / Angstrom s cm**2")
    else:
        assert extracted_max.unit == u.Unit("erg / Angstrom s cm**2 pix**2")


def test_invalid_data_types(cubeviz_helper):
    with pytest.raises(ValueError, match=r"The input file 'does_not_exist\.fits'"):
        cubeviz_helper.load_data('does_not_exist.fits')

    with pytest.raises(NotImplementedError, match='Unsupported data format'):
        cubeviz_helper.load_data(WCS(naxis=3))

    with pytest.raises(NotImplementedError, match='Unsupported data format'):
        cubeviz_helper.load_data(Spectrum(flux=np.ones((2, 2)) * u.nJy, spectral_axis_index=1))

    with pytest.raises(NotImplementedError, match='Unsupported data format'):
        cubeviz_helper.load_data(np.ones((2, 2)))

    with pytest.raises(NotImplementedError, match='Unsupported data format'):
        cubeviz_helper.load_data(np.ones((2, )))
