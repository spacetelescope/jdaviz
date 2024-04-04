import pytest

pytest.importorskip("astropy", minversion="5.3.2")

import numpy as np
from astropy import units as u
from astropy.nddata import NDDataArray, StdDevUncertainty
from astropy.utils.exceptions import AstropyUserWarning
from numpy.testing import assert_allclose, assert_array_equal
from regions import (CirclePixelRegion, CircleAnnulusPixelRegion, EllipsePixelRegion,
                     RectanglePixelRegion, PixCoord)
from specutils import Spectrum1D
from astropy.wcs import WCS


def test_version_after_nddata_update(cubeviz_helper, spectrum1d_cube_with_uncerts):
    # Also test that plugin is disabled before data is loaded.
    plg = cubeviz_helper.plugins['Spectral Extraction']
    assert plg._obj.disabled_msg != ''

    cubeviz_helper.load_data(spectrum1d_cube_with_uncerts)

    spectral_cube = cubeviz_helper.app.data_collection[0].get_object(NDDataArray)
    uncert_cube = cubeviz_helper.app.data_collection[1].get_object(StdDevUncertainty)
    spectral_cube.uncertainty = uncert_cube

    # Collapse the spectral cube using the astropy.nddata machinery.
    # Axes 0, 1 are the spatial ones.
    collapsed_cube_nddata = spectral_cube.sum(axis=(0, 1))  # return NDDataArray

    # Collapse the spectral cube using the methods in jdaviz:
    collapsed_cube_s1d = plg.collapse_to_spectrum(add_data=False)  # returns Spectrum1D

    assert plg._obj.disabled_msg == ''
    assert isinstance(spectral_cube, NDDataArray)
    assert isinstance(collapsed_cube_s1d, Spectrum1D)

    assert_allclose(
        collapsed_cube_nddata.data,
        collapsed_cube_s1d.flux.to_value(collapsed_cube_nddata.unit)
    )


def test_gauss_smooth_before_spec_extract(cubeviz_helper, spectrum1d_cube_with_uncerts):
    # Also test if gaussian smooth plugin is run before spec extract
    # that spec extract yields results of correct cube data
    gs_plugin = cubeviz_helper.plugins['Gaussian Smooth']._obj

    # give uniform unit uncertainties for spec extract test:
    spectrum1d_cube_with_uncerts.uncertainty = StdDevUncertainty(
        np.ones_like(spectrum1d_cube_with_uncerts.data)
    )

    cubeviz_helper.load_data(spectrum1d_cube_with_uncerts)

    gs_plugin.dataset_selected = f'{cubeviz_helper.app.data_collection[0].label}'
    gs_plugin.mode_selected = 'Spatial'
    gs_plugin.stddev = 3

    with pytest.warns(
            AstropyUserWarning,
            match='The following attributes were set on the data object, but will be ignored'):
        gs_plugin.vue_apply()

    gs_data_label = cubeviz_helper.app.data_collection[2].label
    cubeviz_helper.app.add_data_to_viewer('flux-viewer', gs_data_label)

    # create a subset with a single pixel:
    regions = [
        # create a subset with a single pixel:
        CirclePixelRegion(PixCoord(0, 1), radius=0.7),
        # two-pixel region:
        CirclePixelRegion(PixCoord(0.5, 0), radius=1.2)
    ]
    cubeviz_helper.load_regions(regions)

    extract_plugin = cubeviz_helper.plugins['Spectral Extraction']
    extract_plugin.function = "Sum"
    expected_uncert = 2

    extract_plugin.aperture = 'Subset 1'
    collapsed_spec = extract_plugin.collapse_to_spectrum()

    # this single pixel has two wavelengths, and all uncertainties are unity
    # irrespective of which collapse function is applied:
    assert len(collapsed_spec.flux) == 2
    assert_array_equal(collapsed_spec.uncertainty.array, 1)

    # this two-pixel region has four unmasked data points per wavelength:
    extract_plugin.aperture = 'Subset 2'
    collapsed_spec_2 = extract_plugin.collapse_to_spectrum()
    assert_array_equal(collapsed_spec_2.uncertainty.array, expected_uncert)


@pytest.mark.parametrize(
    ("function, expected_uncert"),
    [("Sum", 2), ("Mean", 0.5), ("Min", 1), ("Max", 1)]
)
def test_subset(
    cubeviz_helper, spectrum1d_cube_with_uncerts, function, expected_uncert
):
    # give uniform unit uncertainties for this test:
    spectrum1d_cube_with_uncerts.uncertainty = StdDevUncertainty(
        np.ones_like(spectrum1d_cube_with_uncerts.data)
    )

    regions = [
        # create a subset with a single pixel:
        CirclePixelRegion(PixCoord(0, 1), radius=0.7),
        # two-pixel region:
        CirclePixelRegion(PixCoord(0.5, 0), radius=1.2)
    ]

    cubeviz_helper.load_data(spectrum1d_cube_with_uncerts)
    cubeviz_helper.load_regions(regions)

    plg = cubeviz_helper.plugins['Spectral Extraction']
    plg.function = function

    # single pixel region:
    plg.aperture = 'Subset 1'
    collapsed_spec_1 = plg.collapse_to_spectrum()

    # this single pixel has two wavelengths, and all uncertainties are unity
    # irrespective of which collapse function is applied:
    assert len(collapsed_spec_1.flux) == 2
    assert_array_equal(collapsed_spec_1.uncertainty.array, 1)

    # this two-pixel region has four unmasked data points per wavelength:
    plg.aperture = 'Subset 2'
    collapsed_spec_2 = plg.collapse_to_spectrum()

    assert_array_equal(collapsed_spec_2.uncertainty.array, expected_uncert)


def test_save_collapsed_to_fits(cubeviz_helper, spectrum1d_cube_with_uncerts, tmp_path):

    cubeviz_helper.load_data(spectrum1d_cube_with_uncerts)

    extract_plugin = cubeviz_helper.plugins['Spectral Extraction']

    # make sure export enabled is true, and that before the collapse function
    # is run `collapsed_spec_available` is correctly set to False
    assert extract_plugin._obj.export_enabled
    assert extract_plugin._obj.extracted_spec_available is False

    # run extract function, and make sure `extracted_spec_available` was set to True
    extract_plugin._obj.vue_spectral_extraction()
    assert extract_plugin._obj.extracted_spec_available

    # check that default filename is correct, then change path
    fname = 'extracted_sum_Unknown spectrum object_FLUX.fits'
    fname_path = tmp_path / fname
    assert extract_plugin._obj.filename == fname
    extract_plugin._obj.filename = str(fname_path)

    # save output file with default name, make sure it exists
    extract_plugin._obj.vue_save_as_fits()
    assert fname_path.is_file()

    # read file back in, make sure it matches
    dat = Spectrum1D.read(fname_path)
    assert_array_equal(dat.data, extract_plugin._obj.extracted_spec.data)
    assert dat.unit == extract_plugin._obj.extracted_spec.unit

    # make sure correct error message is raised when export_enabled is False
    # this won't appear in UI, but just to be safe.
    extract_plugin._obj.export_enabled = False
    with pytest.raises(
            ValueError, match="Writing out extracted spectrum to file is currently disabled"):
        extract_plugin._obj.vue_save_as_fits()
    extract_plugin._obj.export_enabled = True  # set back to True

    # check that trying to overwrite without overwrite=True sets overwrite_warn to True, to
    # display popup in UI
    assert extract_plugin._obj.overwrite_warn is False
    extract_plugin._obj.vue_save_as_fits()
    assert extract_plugin._obj.overwrite_warn

    # check that writing out to a non existent directory fails as expected
    extract_plugin._obj.filename = '/this/path/doesnt/exist.fits'
    with pytest.raises(ValueError, match="Invalid path=/this/path/doesnt"):
        extract_plugin._obj.vue_save_as_fits()
    extract_plugin._obj.filename == fname  # set back to original filename


def test_aperture_markers(cubeviz_helper, spectrum1d_cube):

    cubeviz_helper.load_data(spectrum1d_cube)
    cubeviz_helper.load_regions([CirclePixelRegion(PixCoord(0.5, 0), radius=1.2)])

    extract_plg = cubeviz_helper.plugins['Spectral Extraction']
    slice_plg = cubeviz_helper.plugins['Slice']

    mark = extract_plg.aperture.marks[0]
    assert not mark.visible
    with extract_plg.as_active():
        assert mark.visible
        assert not len(mark.x)

        extract_plg.aperture = 'Subset 1'
        before_x = mark.x
        assert len(before_x) > 0

        # sample cube only has 2 slices with wavelengths [4.62280007e-07 4.62360028e-07] m
        slice_values = [4.62280007e-07, 4.62360028e-07]
        slice_plg.value = slice_values[1]
        assert mark.x[1] == before_x[1]

        slice_plg.value = slice_values[0]
        extract_plg._obj.dev_cone_support = True
        extract_plg._obj.wavelength_dependent = True
        assert mark.x[1] == before_x[1]

        slice_plg.value = slice_values[1]
        assert mark.x[1] != before_x[1]

        extract_plg._obj.vue_goto_reference_spectral_value()
        assert_allclose(slice_plg.value, slice_values[0])

        slice_plg.value = slice_values[1]
        extract_plg._obj.vue_adopt_slice_as_reference()
        extract_plg._obj.vue_goto_reference_spectral_value()
        assert_allclose(slice_plg.value, slice_values[1])


@pytest.mark.parametrize('subset', ['Subset 1', 'Subset 2'])
@pytest.mark.parametrize(
    ('aperture_method', 'expected_flux_1000', 'expected_flux_2400'),
    [('Exact',
      [16.51429064, 16.52000853, 16.52572818, 16.53145005, 16.53717344, 16.54289928,
       16.54862712, 16.55435647, 16.56008781, 16.56582186],
      [26.812409, 26.821692, 26.830979, 26.840268, 26.849561, 26.858857,
       26.868156, 26.877459, 26.886765, 26.896074]),
     ('Center', 21, 25)]
)
def test_cone_aperture_with_different_methods(cubeviz_helper, spectrum1d_cube_largest,
                                              subset, aperture_method, expected_flux_1000,
                                              expected_flux_2400):
    cubeviz_helper.load_data(spectrum1d_cube_largest)
    center = PixCoord(5, 10)
    cubeviz_helper.load_regions([
        CirclePixelRegion(center, radius=2.5),
        EllipsePixelRegion(center, width=5, height=5)])

    extract_plg = cubeviz_helper.plugins['Spectral Extraction']

    extract_plg.aperture = subset
    extract_plg.aperture_method.selected = aperture_method
    extract_plg.wavelength_dependent = True
    extract_plg.function = 'Sum'

    collapsed_spec = extract_plg.collapse_to_spectrum()

    assert_allclose(collapsed_spec.flux.value[1000:1010], expected_flux_1000, rtol=1e-6)
    assert_allclose(collapsed_spec.flux.value[2400:2410], expected_flux_2400, rtol=1e-6)

    extract_plg.function = 'Mean'
    collapsed_spec_mean = extract_plg.collapse_to_spectrum()

    assert_allclose(collapsed_spec_mean.flux.value, 1)


@pytest.mark.parametrize('subset', ['Subset 1', 'Subset 2'])
@pytest.mark.parametrize(
    ('aperture_method', 'expected_flux_wav'),
    [('Exact', 19.6349540849),
     ('Center', 21)]
)
def test_cylindrical_aperture_with_different_methods(cubeviz_helper, spectrum1d_cube_largest,
                                                     subset, aperture_method, expected_flux_wav):
    cubeviz_helper.load_data(spectrum1d_cube_largest, data_label="test")
    center = PixCoord(5, 10)
    cubeviz_helper.load_regions([
        CirclePixelRegion(center, radius=2.5),
        EllipsePixelRegion(center, width=5, height=5)])

    extract_plg = cubeviz_helper.plugins['Spectral Extraction']

    extract_plg.aperture = subset
    extract_plg.aperture_method.selected = aperture_method
    extract_plg.wavelength_dependent = False
    extract_plg.function = 'Sum'

    collapsed_spec = extract_plg.collapse_to_spectrum()

    assert_allclose(collapsed_spec.flux.value, expected_flux_wav)

    extract_plg.function = 'Mean'
    collapsed_spec_mean = extract_plg.collapse_to_spectrum()

    assert_allclose(collapsed_spec_mean.flux.value, 1)


# NOTE: Not as thorough as circle and ellipse above but good enough.
def test_rectangle_aperture_with_exact(cubeviz_helper, spectrum1d_cube_largest):
    cubeviz_helper.load_data(spectrum1d_cube_largest)
    cubeviz_helper.load_regions(RectanglePixelRegion(PixCoord(5, 10), width=4, height=4))

    extract_plg = cubeviz_helper.plugins['Spectral Extraction']

    extract_plg.aperture = "Subset 1"
    extract_plg.aperture_method.selected = "Exact"
    extract_plg.wavelength_dependent = True
    extract_plg.function = 'Sum'
    collapsed_spec = extract_plg.collapse_to_spectrum()

    # The extracted spectrum has "steps" (aliased) but perhaps that is due to
    # how photutils is extracting a boxy aperture. There is still a slope.
    expected_flux_step = [9.378906, 10.5625, 11.816406, 13.140625, 14.535156,
                          16, 17.535156, 19.691406, 21.972656, 24.378906]
    assert_allclose(collapsed_spec.flux.value[::301], expected_flux_step)

    extract_plg.wavelength_dependent = False
    collapsed_spec = extract_plg.collapse_to_spectrum()

    assert_allclose(collapsed_spec.flux.value, 16)  # 4 x 4


def test_cone_and_cylinder_errors(cubeviz_helper, spectrum1d_cube_largest):
    cubeviz_helper.load_data(spectrum1d_cube_largest)
    center = PixCoord(5, 10)
    cubeviz_helper.load_regions([
        CirclePixelRegion(center, radius=2.5),
        CircleAnnulusPixelRegion(center, inner_radius=2.5, outer_radius=4)])

    extract_plg = cubeviz_helper.plugins['Spectral Extraction']

    extract_plg.aperture = 'Subset 1'
    extract_plg.aperture_method.selected = 'Exact'
    extract_plg.wavelength_dependent = True

    extract_plg.function = 'Min'
    with pytest.raises(ValueError, match=extract_plg._obj.conflicting_aperture_error_message):
        extract_plg.collapse_to_spectrum()

    extract_plg.function = 'Max'
    with pytest.raises(ValueError, match=extract_plg._obj.conflicting_aperture_error_message):
        extract_plg.collapse_to_spectrum()

    extract_plg.function = 'Sum'
    extract_plg.aperture = 'Subset 2'
    with pytest.raises(NotImplementedError, match=".* is not supported"):
        extract_plg.collapse_to_spectrum()


def test_cone_aperture_with_frequency_units(cubeviz_helper, spectral_cube_wcs):
    data = Spectrum1D(flux=np.ones((128, 129, 256)) * u.nJy, wcs=spectral_cube_wcs)
    cubeviz_helper.load_data(data, data_label="Test Flux")
    cubeviz_helper.load_regions([CirclePixelRegion(PixCoord(14, 15), radius=2.5)])

    extract_plg = cubeviz_helper.plugins['Spectral Extraction']

    extract_plg.aperture = 'Subset 1'
    extract_plg.aperture_method.selected = 'Exact'
    extract_plg.wavelength_dependent = True
    extract_plg.function = 'Sum'

    with pytest.raises(ValueError, match="Spectral axis unit physical type is"):
        extract_plg.collapse_to_spectrum()


def test_cube_extraction_with_nan(cubeviz_helper, image_cube_hdu_obj):
    image_cube_hdu_obj[1].data[:, :2, :2] = np.nan
    cubeviz_helper.load_data(image_cube_hdu_obj, data_label="with_nan")
    extract_plg = cubeviz_helper.plugins['Spectral Extraction']
    sp = extract_plg.collapse_to_spectrum()  # Default settings (sum)
    assert_allclose(sp.flux.value, 96)  # (10 x 10) - 4

    cubeviz_helper.load_regions(RectanglePixelRegion(PixCoord(1.5, 1.5), width=4, height=4))
    extract_plg.aperture = 'Subset 1'
    sp_subset = extract_plg.collapse_to_spectrum()  # Default settings but on Subset
    assert_allclose(sp_subset.flux.value, 12)  # (4 x 4) - 4


def test_unit_translation(cubeviz_helper):
    # custom cube so we have PIXAR_SR in metadata, and flux units = Jy/pix
    wcs_dict = {"CTYPE1": "WAVE-LOG", "CTYPE2": "DEC--TAN", "CTYPE3": "RA---TAN",
                "CRVAL1": 4.622e-7, "CRVAL2": 27, "CRVAL3": 205,
                "CDELT1": 8e-11, "CDELT2": 0.0001, "CDELT3": -0.0001,
                "CRPIX1": 0, "CRPIX2": 0, "CRPIX3": 0, "PIXAR_SR": 8e-11}
    w = WCS(wcs_dict)
    flux = np.zeros((30, 20, 3001), dtype=np.float32)
    flux[5:15, 1:11, :] = 1
    cube = Spectrum1D(flux=flux * u.MJy, wcs=w, meta=wcs_dict)
    cubeviz_helper.load_data(cube, data_label="test")

    center = PixCoord(5, 10)
    cubeviz_helper.load_regions(CirclePixelRegion(center, radius=2.5))

    extract_plg = cubeviz_helper.plugins['Spectral Extraction']

    extract_plg.aperture = extract_plg.aperture.choices[-1]
    extract_plg.aperture_method.selected = 'Exact'
    extract_plg.wavelength_dependent = True
    extract_plg.function = 'Sum'
    # set so pixel scale factor != 1
    extract_plg.reference_spectral_value = 0.000001

    # collapse to spectrum, now we can get pixel scale factor
    collapsed_spec = extract_plg.collapse_to_spectrum()

    assert collapsed_spec.meta['_pixel_scale_factor'] != 1

    # store to test second time after calling translate_units
    mjy_sr_data1 = collapsed_spec._data[0]

    extract_plg._obj.translate_units(collapsed_spec)

    assert collapsed_spec._unit == u.MJy / u.sr
    # some value in MJy/sr that we know the outcome after translation
    assert np.allclose(collapsed_spec._data[0], 8.7516529e10)

    extract_plg._obj.translate_units(collapsed_spec)

    # translating again returns the original units
    assert collapsed_spec._unit == u.MJy
    # returns to the original values
    # which is a value in Jy/pix that we know the outcome after translation
    assert np.allclose(collapsed_spec._data[0], mjy_sr_data1)
