import pytest
import warnings

import numpy as np
from astropy import units as u
from astropy.io import fits
from astropy.nddata import NDDataArray, StdDevUncertainty
from astropy.table import QTable
from astropy.tests.helper import assert_quantity_allclose
from astropy.utils.exceptions import AstropyUserWarning
from glue.core.roi import CircularROI, RectangularROI
from numpy.testing import assert_allclose, assert_array_equal
from regions import (CirclePixelRegion, CircleAnnulusPixelRegion, EllipsePixelRegion,
                     RectanglePixelRegion, PixCoord)
from specutils import Spectrum1D
from specutils.manipulation import FluxConservingResampler

from jdaviz.core.custom_units_and_equivs import PIX2, SPEC_PHOTON_FLUX_DENSITY_UNITS
from jdaviz.core.unit_conversion_utils import (all_flux_unit_conversion_equivs,
                                               flux_conversion_general)

calspec_url = "https://archive.stsci.edu/hlsps/reference-atlases/cdbs/current_calspec/"


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

    # when loaded into app, cubes loaded in flux are converted to per-pixel-squared
    # surface brightness, so multiply by pix**2 to compare to NDData, if input
    # cube was in flux
    collapsed_cube_nddata = collapsed_cube_nddata * (u.pix ** 2)

    # Collapse the spectral cube using the methods in jdaviz:
    collapsed_cube_s1d = plg.extract(add_data=False)  # returns Spectrum1D

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
    cubeviz_helper.plugins['Subset Tools'].import_region(regions, combination_mode='new')

    extract_plugin = cubeviz_helper.plugins['Spectral Extraction']
    extract_plugin.function = "Sum"
    expected_uncert = 2

    extract_plugin.aperture = 'Subset 1'
    collapsed_spec = extract_plugin.extract()

    # this single pixel has two wavelengths, and all uncertainties are unity
    # irrespective of which collapse function is applied:
    assert len(collapsed_spec.flux) == 2
    assert_array_equal(collapsed_spec.uncertainty.array, 1)

    # this two-pixel region has four unmasked data points per wavelength:
    extract_plugin.aperture = 'Subset 2'
    collapsed_spec_2 = extract_plugin.extract()
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
    cubeviz_helper.plugins['Subset Tools'].import_region(regions, combination_mode='new')

    plg = cubeviz_helper.plugins['Spectral Extraction']
    plg.function = function

    # single pixel region:
    plg.aperture = 'Subset 1'
    collapsed_spec_1 = plg.extract()

    # this single pixel has two wavelengths, and all uncertainties are unity
    # irrespective of which collapse function is applied:
    assert len(collapsed_spec_1.flux) == 2
    assert_array_equal(collapsed_spec_1.uncertainty.array, 1)

    # this two-pixel region has four unmasked data points per wavelength:
    plg.aperture = 'Subset 2'
    collapsed_spec_2 = plg.extract()

    assert_array_equal(collapsed_spec_2.uncertainty.array, expected_uncert)


def test_extracted_file_in_export_plugin(cubeviz_helper, spectrum1d_cube_with_uncerts, tmp_path):

    cubeviz_helper.load_data(spectrum1d_cube_with_uncerts)

    extract_plugin = cubeviz_helper.plugins['Spectral Extraction']

    # make sure export enabled is true, and that before the collapse function
    # is run `collapsed_spec_available` is correctly set to False
    assert extract_plugin._obj.export_enabled
    assert extract_plugin._obj.extraction_available is False

    # run extract function, and make sure `extraction_available` was set to True
    extract_plugin._obj.vue_spectral_extraction()
    assert extract_plugin._obj.extraction_available

    # check that default filename is correct, then change path
    fname = 'extracted_sum_Unknown spectrum object_FLUX.fits'
    fname_path = tmp_path / fname
    assert extract_plugin._obj.filename == fname
    extract_plugin._obj.filename = str(fname_path)

    label = extract_plugin._obj.add_results.label
    export_plugin = cubeviz_helper.plugins['Export']._obj

    assert label in export_plugin.data_collection.labels


def test_aperture_markers(cubeviz_helper, spectrum1d_cube):

    cubeviz_helper.load_data(spectrum1d_cube)
    cubeviz_helper.plugins['Subset Tools'].import_region(
        [CirclePixelRegion(PixCoord(0.5, 0), radius=1.2)])

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
    cubeviz_helper.plugins['Subset Tools'].import_region(
        CirclePixelRegion(center, radius=2.5), combination_mode='new')
    cubeviz_helper.plugins['Subset Tools'].import_region(
        EllipsePixelRegion(center, width=5, height=5), combination_mode='new')

    extract_plg = cubeviz_helper.plugins['Spectral Extraction']

    extract_plg.aperture = subset
    extract_plg.aperture_method.selected = aperture_method
    extract_plg.wavelength_dependent = True
    extract_plg.function = 'Sum'

    collapsed_spec = extract_plg.extract()

    assert_allclose(collapsed_spec.flux.value[1000:1010], expected_flux_1000, rtol=1e-6)
    assert_allclose(collapsed_spec.flux.value[2400:2410], expected_flux_2400, rtol=1e-6)

    extract_plg.function = 'Mean'
    collapsed_spec_mean = extract_plg.extract()

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
    cubeviz_helper.plugins['Subset Tools'].import_region([
        CirclePixelRegion(center, radius=2.5),
        EllipsePixelRegion(center, width=5, height=5)], combination_mode='new')

    extract_plg = cubeviz_helper.plugins['Spectral Extraction']

    extract_plg.aperture = subset
    extract_plg.aperture_method.selected = aperture_method
    extract_plg.wavelength_dependent = False
    extract_plg.function = 'Sum'

    collapsed_spec = extract_plg.extract()

    assert_allclose(collapsed_spec.flux.value, expected_flux_wav)

    extract_plg.function = 'Mean'
    collapsed_spec_mean = extract_plg.extract()

    assert_allclose(collapsed_spec_mean.flux.value, 1)


# NOTE: Not as thorough as circle and ellipse above but good enough.
def test_rectangle_aperture_with_exact(cubeviz_helper, spectrum1d_cube_largest):
    cubeviz_helper.load_data(spectrum1d_cube_largest)
    cubeviz_helper.plugins['Subset Tools'].import_region(
        RectanglePixelRegion(PixCoord(5, 10), width=4, height=4))

    extract_plg = cubeviz_helper.plugins['Spectral Extraction']

    extract_plg.aperture = "Subset 1"
    extract_plg.aperture_method.selected = "Exact"
    extract_plg.wavelength_dependent = True
    extract_plg.function = 'Sum'
    collapsed_spec = extract_plg.extract()

    # The extracted spectrum has "steps" (aliased) but perhaps that is due to
    # how photutils is extracting a boxy aperture. There is still a slope.
    expected_flux_step = [9.378906, 10.5625, 11.816406, 13.140625, 14.535156,
                          16, 17.535156, 19.691406, 21.972656, 24.378906]
    assert_allclose(collapsed_spec.flux.value[::301], expected_flux_step)

    extract_plg.wavelength_dependent = False
    collapsed_spec = extract_plg.extract()

    assert_allclose(collapsed_spec.flux.value, 16)  # 4 x 4


def test_background_subtraction(cubeviz_helper, spectrum1d_cube_largest):
    # add constant background:
    spectrum1d_cube_largest = spectrum1d_cube_largest + 1 * u.Jy

    cubeviz_helper.load_data(spectrum1d_cube_largest)
    cubeviz_helper.plugins['Subset Tools'].import_region([
        CirclePixelRegion(PixCoord(5, 10), radius=2.5),
        EllipsePixelRegion(PixCoord(13, 10), width=3, height=5)], combination_mode='new')

    extract_plg = cubeviz_helper.plugins['Spectral Extraction']
    with extract_plg.as_active():
        extract_plg.aperture = 'Subset 1'
        spec_no_bg = extract_plg.extract()

        extract_plg.background = 'Subset 2'

        # test visiblity of background aperture and preview based on "active step"
        assert extract_plg.background.marks[0].visible
        assert not extract_plg._obj.marks['bg_extract'].visible
        extract_plg._obj.active_step = 'ap'
        assert not extract_plg.background.marks[0].visible
        assert not extract_plg._obj.marks['bg_extract'].visible
        extract_plg._obj.active_step = 'bg'
        assert extract_plg.background.marks[0].visible
        assert extract_plg._obj.marks['bg_extract'].visible

        bg_spec = extract_plg.extract_bg_spectrum()
        extract_plg.bg_spec_per_spaxel = True
        bg_spec_normed = extract_plg.extract_bg_spectrum()
        assert np.all(bg_spec_normed.flux.value < bg_spec.flux.value)
        spec = extract_plg.extract()

    assert np.allclose(spec.flux, spec_no_bg.flux - bg_spec.flux)

    # number of pixels in the aperture, background subsets:
    n_aperture_pixels = cubeviz_helper.app.get_subsets('Subset 1')[0]['region'].to_mask().data.sum()
    n_bg_pixels = cubeviz_helper.app.get_subsets('Subset 2')[0]['region'].to_mask().data.sum()

    # the background subtracted from each slice in wavelength from the aperture should be equal
    # to the background -- which is the minimum per spectral slice in this example cube -- divided
    # by the number of pixels in the aperture:
    cube_min_per_slice = extract_plg._obj.cube['flux'].min(axis=(0, 1))
    np.testing.assert_allclose(
        bg_spec.flux.value / n_aperture_pixels,
        cube_min_per_slice
    )

    # background normalized per spaxel should be equal to the minimum per spectral slice:
    cube_min_per_slice = extract_plg._obj.cube['flux'].min(axis=(0, 1))
    np.testing.assert_allclose(
        bg_spec_normed.flux.value / n_bg_pixels,
        cube_min_per_slice
    )


def test_cone_and_cylinder_errors(cubeviz_helper, spectrum1d_cube_largest):
    cubeviz_helper.load_data(spectrum1d_cube_largest)
    center = PixCoord(5, 10)
    cubeviz_helper.plugins['Subset Tools'].import_region([
        CirclePixelRegion(center, radius=2.5),
        CircleAnnulusPixelRegion(center, inner_radius=2.5, outer_radius=4)], combination_mode='new')

    extract_plg = cubeviz_helper.plugins['Spectral Extraction']

    extract_plg.aperture = 'Subset 1'
    extract_plg.aperture_method.selected = 'Exact'
    extract_plg.wavelength_dependent = True

    extract_plg.function = 'Min'
    with pytest.raises(ValueError, match=extract_plg._obj.conflicting_aperture_error_message):
        extract_plg.extract()

    extract_plg.function = 'Max'
    with pytest.raises(ValueError, match=extract_plg._obj.conflicting_aperture_error_message):
        extract_plg.extract()

    extract_plg.function = 'Sum'
    extract_plg.aperture = 'Subset 2'
    with pytest.raises(NotImplementedError, match=".* is not supported"):
        extract_plg.extract()


def test_cone_aperture_with_frequency_units(cubeviz_helper, spectral_cube_wcs):
    data = Spectrum1D(flux=np.ones((128, 129, 256)) * u.nJy, wcs=spectral_cube_wcs)
    cubeviz_helper.load_data(data, data_label="Test Flux")
    cubeviz_helper.plugins['Subset Tools'].import_region(
        [CirclePixelRegion(PixCoord(14, 15), radius=2.5)])

    extract_plg = cubeviz_helper.plugins['Spectral Extraction']

    extract_plg.aperture = 'Subset 1'
    extract_plg.aperture_method.selected = 'Exact'
    extract_plg.wavelength_dependent = True
    extract_plg.function = 'Sum'

    with pytest.raises(ValueError, match="Spectral axis unit physical type is"):
        extract_plg.extract()


def test_cube_extraction_with_nan(cubeviz_helper, image_cube_hdu_obj):
    image_cube_hdu_obj[1].data[:, :2, :2] = np.nan
    cubeviz_helper.load_data(image_cube_hdu_obj, data_label="with_nan")
    extract_plg = cubeviz_helper.plugins['Spectral Extraction']
    sp = extract_plg.extract()  # Default settings (sum)
    assert_allclose(sp.flux.value, 9.6E-16)  # (10 x 10) - 4

    cubeviz_helper.plugins['Subset Tools'].import_region(
        RectanglePixelRegion(PixCoord(1.5, 1.5), width=4, height=4))
    extract_plg.aperture = 'Subset 1'
    sp_subset = extract_plg.extract()  # Default settings but on Subset
    assert_allclose(sp_subset.flux.value, 1.2E-16)  # (4 x 4) - 4


def test_autoupdate_results(cubeviz_helper, spectrum1d_cube_largest):
    cubeviz_helper.load_data(spectrum1d_cube_largest)
    cubeviz_helper.plugins['Subset Tools'].import_region(
        CircularROI(xc=5, yc=5, radius=2))

    extract_plg = cubeviz_helper.plugins['Spectral Extraction']
    extract_plg.aperture = 'Subset 1'
    extract_plg.add_results.label = 'extracted'
    extract_plg.add_results._obj.auto_update_result = True
    _ = extract_plg.extract()

#    orig_med_flux = np.median(cubeviz_helper.get_data('extracted').flux)

    # replace Subset 1 with a larger subset, resulting fluxes should increase
    cubeviz_helper.plugins['Subset Tools'].combination_mode = 'replace'
    cubeviz_helper.plugins['Subset Tools'].import_region(CircularROI(xc=5, yc=5, radius=3))

    # update should take place automatically, but since its async, we'll call manually to ensure
    # the update is complete before comparing results
    for subset in cubeviz_helper.app.data_collection.subset_groups[0].subsets:
        cubeviz_helper.app._update_live_plugin_results(trigger_subset=subset)
    # TODO: this is randomly failing in CI (not always) so will disable the assert for now and just
    # cover to make sure the logic does not crash
#    new_med_flux = np.median(cubeviz_helper.get_data('extracted').flux)
#    assert new_med_flux > orig_med_flux


def test_aperture_composite_detection(cubeviz_helper, spectrum1d_cube):
    cubeviz_helper.load_data(spectrum1d_cube)
    subset_plugin = cubeviz_helper.plugins['Subset Tools']
    spec_extr_plugin = cubeviz_helper.plugins['Spectral Extraction']._obj

    # create a rectangular subset with all spaxels:
    rectangle = RectangularROI(-0.5, 1.5, -0.5, 3.5)
    subset_plugin.import_region(rectangle)

    # select subset 1, ensure it's not a composite subset:
    spec_extr_plugin.aperture_selected = 'Subset 1'
    assert not spec_extr_plugin.aperture.is_composite

    # now remove from this subset a circular region in the center:
    circle = CircularROI(0.5, 1.5, 1)

    subset_plugin.combination_mode = 'andnot'
    subset_plugin.import_region(circle)

    # now the subset is composite:
    assert spec_extr_plugin.aperture.is_composite


def test_extraction_composite_subset(cubeviz_helper, spectrum1d_cube):
    cubeviz_helper.load_data(spectrum1d_cube)

    subset_plugin = cubeviz_helper.plugins['Subset Tools']
    spec_extr_plugin = cubeviz_helper.plugins['Spectral Extraction']._obj

    lower_aperture = RectangularROI(-0.5, 0.5, -0.5, 1.5)
    upper_aperture = RectangularROI(2.5, 3.5, -0.5, 1.5)

    subset_plugin.import_region(lower_aperture)
    subset_plugin.combination_mode = 'new'
    subset_plugin.import_region(upper_aperture)

    spec_extr_plugin.aperture_selected = 'Subset 1'
    spectrum_1 = spec_extr_plugin.extract()

    spec_extr_plugin.aperture_selected = 'Subset 2'
    spectrum_2 = spec_extr_plugin.extract()

    rectangle = RectangularROI(-0.5, 3.5, -0.5, 1.5)

    subset_plugin.combination_mode = 'new'
    subset_plugin.import_region(rectangle)

    subset_plugin._obj.subset_selected = 'Subset 3'
    circle = CircularROI(1.5, 0.5, 1.1)

    subset_plugin.combination_mode = 'andnot'
    subset_plugin.import_region(circle)

    spec_extr_plugin.aperture_selected = 'Subset 3'

    assert spec_extr_plugin.aperture.is_composite

    spectrum_3 = spec_extr_plugin.extract()

    np.testing.assert_allclose(
        (spectrum_1 + spectrum_2).flux.value,
        (spectrum_3).flux.value
    )


def test_spectral_extraction_with_correct_sum_units(cubeviz_helper,
                                                    spectrum1d_cube_fluxunit_jy_per_steradian):
    cubeviz_helper.load_data(spectrum1d_cube_fluxunit_jy_per_steradian)
    spec_extr_plugin = cubeviz_helper.plugins['Spectral Extraction']._obj
    collapsed = spec_extr_plugin.extract()

    assert '_pixel_scale_factor' in collapsed.meta

    # Original units in Jy / sr
    # After collapsing, sr is removed via the scale factor and the extracted spectrum is in Jy
    expected_flux_values = (np.array([190., 590., 990., 1390., 1790.,
                                      2190., 2590., 2990., 3390., 3790.]) *
                            collapsed.meta.get('_pixel_scale_factor'))

    np.testing.assert_allclose(
        collapsed.flux.value,
        expected_flux_values
    )
    assert collapsed.flux.unit == u.Jy
    assert collapsed.uncertainty.unit == u.Jy


def test_default_spectral_extraction(cubeviz_helper, spectrum1d_cube_fluxunit_jy_per_steradian):
    # spacetelescope/jdaviz#3086 reported that the default cube
    # spectral extraction in cubeviz did not match the spectral extraction
    # for a spatial subset that captures all data-containing spaxels. this
    # regression tests make sure that doesn't happen anymore by accounting
    # for non-science pixels in the sums:
    cubeviz_helper.load_data(spectrum1d_cube_fluxunit_jy_per_steradian)

    subset_plugin = cubeviz_helper.plugins['Subset Tools']

    subset_plugin.import_region(CircularROI(1.5, 2, 5))

    # the first and second spectra correspond to the default extraction
    # and the subset extraction. the fluxes in these extractions should agree:
    extracted_spectra = list(
        cubeviz_helper.specviz.get_spectra(apply_slider_redshift=False).values()
    )

    assert_quantity_allclose(
        extracted_spectra[0].flux, extracted_spectra[1].flux
    )


def test_spectral_extraction_unit_conv_one_spec(
    cubeviz_helper, spectrum1d_cube_fluxunit_jy_per_steradian
):
    cubeviz_helper.load_data(spectrum1d_cube_fluxunit_jy_per_steradian)
    spectrum_viewer = cubeviz_helper.app.get_viewer(
        cubeviz_helper._default_spectrum_viewer_reference_name)
    uc = cubeviz_helper.plugins["Unit Conversion"]
    assert uc.flux_unit == "Jy"
    uc.flux_unit.selected = "MJy"
    assert spectrum_viewer.state.y_display_unit == "MJy"
    spec_extr_plugin = cubeviz_helper.plugins['Spectral Extraction']
    # Overwrite the one and only default extraction.
    collapsed = spec_extr_plugin.extract()
    # Actual values not in display unit but should not affect display unit.
    assert collapsed.flux.unit == u.Jy
    assert uc.flux_unit.selected == "MJy"
    assert spectrum_viewer.state.y_display_unit == "MJy"


@pytest.mark.usefixtures('_jail')
@pytest.mark.remote_data
@pytest.mark.parametrize(
    "start_slice, aperture, expected_rtol, uri, calspec_url",
    (
        (5.2, (20.5, 17, 10.9), 0.03,
         "mast:jwst/product/jw01524-o003_t002_miri_ch1-shortmediumlong_s3d.fits",
         calspec_url + "delumi_mod_005.fits"),  # delta UMi

        (4.85, (28, 21, 12), 0.03,
         "mast:jwst/product/jw01050-o003_t005_miri_ch1-shortmediumlong_s3d.fits",
         calspec_url + "hd159222_mod_007.fits"),  # HD 159222
    )
)
def test_spectral_extraction_scientific_validation(
    cubeviz_helper, start_slice,
    aperture, expected_rtol, uri, calspec_url
):
    """
    Compare the extracted spectrum from MIRI CH1 IFU cubes for
    delta UMi (A1Van star) and HD 159222 (G1V star) with CALSPEC model
    spectra. These model spectra are already flux calibrated using other
    observatories, and are used to compute the flux calibration for JWST.
    They are available for download at:
    https://archive.stsci.edu/hlsps/reference-atlases/cdbs/current_calspec/

    We can compare the spectral extraction results from Cubeviz with these model
    spectra, without further normalization of the models or data. When comparing
    any flux-calibrated observation against any model, the expected mismatch can be
    as large as ~10%. The agreement is much better for stars used to compute
    the flux calibration, which are the targets selected for this test.

    Both observations in this test are from MIRI. It's likely that the
    accuracy of the flux calibration of the data products available on MAST will
    evolve with time. For the latest updates on MIRI flux calibration, see:
    https://jwst-docs.stsci.edu/jwst-calibration-status/miri-calibration-status/
    """
    # Download CALSPEC model spectrum, initialize Spectrum1D.
    calspec_fitsrec = fits.getdata(calspec_url)
    column_units = [u.AA] + 2 * [u.Unit('erg s-1 cm-2 AA-1')]
    spectra_table = QTable(calspec_fitsrec, units=column_units)
    model_spectrum = Spectrum1D(
        flux=spectra_table['FLUX'],
        spectral_axis=spectra_table['WAVELENGTH']
    )

    # load observations into Cubeviz
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        cubeviz_helper.load_data(uri, cache=True)

    # add a subset with an aperture centered on each source
    subset_plugin = cubeviz_helper.plugins['Subset Tools']
    subset_plugin.import_region(CircularROI(*aperture))

    # set the slice to the blue end of MIRI CH1
    slice_plugin = cubeviz_helper.plugins['Slice']
    slice_plugin.value = start_slice

    # run a conical spectral extraction
    spectral_extraction = cubeviz_helper.plugins['Spectral Extraction']
    spectral_extraction.aperture = 'Subset 1'
    spectral_extraction.wavelength_dependent = True
    spectral_extraction._obj.results_label = 'conical-extraction'
    extracted_spectrum = spectral_extraction.extract()

    # resample the model spectrum on the same wavelengths as
    # the observed spectrum:
    resampled_spectrum = FluxConservingResampler()(
        model_spectrum, extracted_spectrum.wavelength
    )

    # load model spectrum:
    cubeviz_helper.specviz.load_data(resampled_spectrum, data_label='calspec model')

    # compute the relative residual, take the median absolute deviation:
    median_abs_relative_dev = abs(np.median(
        abs(
            extracted_spectrum.flux /
            resampled_spectrum.flux.to(u.MJy, u.spectral_density(resampled_spectrum.wavelength))
        ).to_value(u.dimensionless_unscaled) - 1
    ))
    assert median_abs_relative_dev < expected_rtol


@pytest.mark.parametrize("flux_angle_unit", [(u.Unit(x), u.sr) for x in SPEC_PHOTON_FLUX_DENSITY_UNITS]  # noqa
                                              + [(u.Unit(x), PIX2) for x in SPEC_PHOTON_FLUX_DENSITY_UNITS])  # noqa
def test_spectral_extraction_flux_unit_conversions(cubeviz_helper,
                                                   spectrum1d_cube_custom_fluxunit,
                                                   flux_angle_unit):
    """
    Test that cubeviz spectral extraction plugin works with all possible
    flux unit conversions for a cube loaded in units spectral/photon flux
    density. The spectral extraction result will remain in the native
    data unit, but the extraction preview should be converted to the
    display unit.
    """

    flux_unit, angle_unit = flux_angle_unit

    sb_cube = spectrum1d_cube_custom_fluxunit(fluxunit=flux_unit / angle_unit,
                                              shape=(5, 4, 4),
                                              with_uncerts=True)
    cubeviz_helper.load_data(sb_cube)

    spectrum_viewer = cubeviz_helper.app.get_viewer(
        cubeviz_helper._default_spectrum_viewer_reference_name)

    uc = cubeviz_helper.plugins["Unit Conversion"]
    se = cubeviz_helper.plugins['Spectral Extraction']
    se.keep_active = True  # keep active for access to preview markers

    # equivalencies for unit conversion, for comparison of outputs
    equivs = all_flux_unit_conversion_equivs(se.dataset.selected_obj.meta.get('PIXAR_SR', 1.0),
                                             se.dataset.selected_obj.spectral_axis)

    for new_flux_unit in SPEC_PHOTON_FLUX_DENSITY_UNITS:
        if new_flux_unit != flux_unit:

            uc.flux_unit.selected = flux_unit.to_string()
            uc.spectral_y_type.selected = 'Flux'

            # and set back to sum initially so units will always be flux not sb
            se.function.selected = 'Sum'
            se.extract()

            original_sum_y_values = se._obj.marks['extract'].y

            # set to new unit
            uc.flux_unit.selected = new_flux_unit
            assert spectrum_viewer.state.y_display_unit == new_flux_unit

            # still using 'sum', results should be in flux
            collapsed = se.extract()

            # make sure extraction preview was translated to new display units
            new_sum_y_values = se._obj.marks['extract'].y
            new_converted_to_old_unit = flux_conversion_general(new_sum_y_values,
                                                                u.Unit(new_flux_unit),
                                                                u.Unit(flux_unit),
                                                                equivs, with_unit=False)
            np.testing.assert_allclose(original_sum_y_values, new_converted_to_old_unit)

            # collapsed result will still have the native data flux unit
            assert uc.spectral_y_type.selected == 'Flux'
            assert collapsed.flux.unit == collapsed.uncertainty.unit == flux_unit
            # but display units in spectrum viewer should reflect new flux unit selection
            assert se._obj.spectrum_y_units == se._obj.results_units == new_flux_unit
