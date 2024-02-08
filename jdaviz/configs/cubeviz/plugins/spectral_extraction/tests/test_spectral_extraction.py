import os
import pytest
from packaging.version import Version
import numpy as np
import astropy
from astropy.nddata import NDDataArray, StdDevUncertainty
from specutils import Spectrum1D
from regions import CirclePixelRegion, PixCoord
from astropy.utils.exceptions import AstropyUserWarning

ASTROPY_LT_5_3_2 = Version(astropy.__version__) < Version('5.3.2')


@pytest.mark.skipif(not ASTROPY_LT_5_3_2, reason='Needs astropy <5.3.2')
def test_version_before_nddata_update(cubeviz_helper, spectrum1d_cube_with_uncerts):
    # Also test that plugin is disabled before data is loaded.
    plg = cubeviz_helper.plugins['Spectral Extraction']
    assert plg._obj.disabled_msg != ''


@pytest.mark.skipif(ASTROPY_LT_5_3_2, reason='Needs astropy 5.3.2 or later')
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

    np.testing.assert_allclose(
        collapsed_cube_nddata.data,
        collapsed_cube_s1d.flux.to_value(collapsed_cube_nddata.unit)
    )


@pytest.mark.skipif(ASTROPY_LT_5_3_2, reason='Needs astropy 5.3.2 or later')
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
    assert np.all(np.equal(collapsed_spec.uncertainty.array, 1))

    # this two-pixel region has four unmasked data points per wavelength:
    extract_plugin.aperture = 'Subset 2'
    collapsed_spec_2 = extract_plugin.collapse_to_spectrum()
    assert np.all(np.equal(collapsed_spec_2.uncertainty.array, expected_uncert))


@pytest.mark.skipif(ASTROPY_LT_5_3_2, reason='Needs astropy 5.3.2 or later')
@pytest.mark.parametrize(
    "function, expected_uncert",
    zip(
        ["Sum", "Mean", "Min", "Max"],
        [2, 0.5, 1, 1]
    )
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
    assert np.all(np.equal(collapsed_spec_1.uncertainty.array, 1))

    # this two-pixel region has four unmasked data points per wavelength:
    plg.aperture = 'Subset 2'
    collapsed_spec_2 = plg.collapse_to_spectrum()

    assert np.all(np.equal(collapsed_spec_2.uncertainty.array, expected_uncert))


def test_save_collapsed_to_fits(cubeviz_helper, spectrum1d_cube_with_uncerts, tmpdir):

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
    assert extract_plugin._obj.filename == fname
    extract_plugin._obj.filename = os.path.join(tmpdir, fname)

    # save output file with default name, make sure it exists
    extract_plugin._obj.vue_save_as_fits()
    assert os.path.isfile(os.path.join(tmpdir, fname))

    # read file back in, make sure it matches
    dat = Spectrum1D.read(os.path.join(tmpdir, fname))
    assert np.all(dat.data == extract_plugin._obj.extracted_spec.data)
    assert dat.unit == extract_plugin._obj.extracted_spec.unit

    # make sure correct error message is raised when export_enabled is False
    # this won't appear in UI, but just to be safe.
    extract_plugin._obj.export_enabled = False
    msg = "Writing out extracted spectrum to file is currently disabled"
    with pytest.raises(ValueError, match=msg):
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
        slice_plg.slice = 1
        assert mark.x[1] == before_x[1]

        slice_plg.slice = 0
        extract_plg._obj.dev_cone_support = True
        extract_plg._obj.wavelength_dependent = True
        assert mark.x[1] == before_x[1]

        slice_plg.slice = 1
        assert mark.x[1] != before_x[1]

        extract_plg._obj.vue_goto_reference_wavelength()
        assert slice_plg.slice == 0

        slice_plg.slice = 1
        extract_plg._obj.vue_adopt_slice_as_reference()
        extract_plg._obj.vue_goto_reference_wavelength()
        assert slice_plg.slice == 1


def test_cone_aperture(cubeviz_helper, spectrum1d_cube_largest):
    cubeviz_helper.load_data(spectrum1d_cube_largest)
    cubeviz_helper.load_regions([CirclePixelRegion(PixCoord(1, 1), radius=0.5)])

    mask_cube = Spectrum1D(flux=np.ones_like(spectrum1d_cube_largest.flux),
                           spectral_axis=spectrum1d_cube_largest.spectral_axis)
    cubeviz_helper.load_data(mask_cube, override_cube_limit=True)
    cubeviz_helper._loaded_mask_cube = cubeviz_helper.app.data_collection[-1]

    extract_plg = cubeviz_helper.plugins['Spectral Extraction']
    slice_plg = cubeviz_helper.plugins['Slice']

    extract_plg.aperture = 'Subset 1'
    extract_plg.wavelength_dependent = True
    assert cubeviz_helper._loaded_mask_cube.get_object(cls=Spectrum1D, statistic=None)

    slice_plg.slice = 1
    extract_plg._obj.vue_adopt_slice_as_reference()
    cone_aperture = extract_plg._obj.cone_aperture()
    assert (cone_aperture.shape ==
            cubeviz_helper._loaded_flux_cube.get_object(cls=Spectrum1D, statistic=None).shape)

    # Make sure that the cone created when the reference slice is 988 is different
    # to the cone made at reference slice 1.
    slice_plg.slice = 988
    extract_plg._obj.vue_adopt_slice_as_reference()
    cone_aperture_2 = extract_plg._obj.cone_aperture()

    assert not (cone_aperture == cone_aperture_2).all()
