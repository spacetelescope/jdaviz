import numpy as np
import pytest
from astropy import units as u
from astropy.tests.helper import assert_quantity_allclose
from astropy.utils.exceptions import AstropyUserWarning
from numpy.testing import assert_allclose
from regions import RectanglePixelRegion, PixCoord


def test_cubeviz_aperphot_cube_orig_flux(cubeviz_helper, image_cube_hdu_obj_microns):
    cubeviz_helper.load_data(image_cube_hdu_obj_microns, data_label="test")
    flux_unit = u.Unit("1E-17 erg*s^-1*cm^-2*Angstrom^-1")

    aper = RectanglePixelRegion(center=PixCoord(x=1, y=2), width=3, height=5)
    cubeviz_helper.load_regions(aper)

    # Make sure MASK is not an option even when shown in viewer.
    cubeviz_helper.app.add_data_to_viewer("flux-viewer", "test[MASK]", visible=True)

    plg = cubeviz_helper.plugins["Aperture Photometry"]._obj
    assert plg.dataset.labels == ["test[FLUX]", "test[ERR]"]
    assert plg.cube_slice == "4.894e+00 um"

    plg.dataset_selected = "test[FLUX]"
    plg.aperture_selected = "Subset 1"
    plg.vue_do_aper_phot()
    row = cubeviz_helper.get_aperture_photometry_results()[0]

    # Basically, we should recover the input rectangle here.
    assert_allclose(row["xcenter"], 1 * u.pix)
    assert_allclose(row["ycenter"], 2 * u.pix)
    sky = row["sky_center"]
    assert_allclose(sky.ra.deg, 205.43985906934287)
    assert_allclose(sky.dec.deg, 27.003490103642033)
    assert_allclose(row["sum"], 75 * flux_unit)  # 3 (w) x 5 (h) x 5 (v)
    assert_allclose(row["sum_aper_area"], 15 * (u.pix * u.pix))  # 3 (w) x 5 (h)
    assert_allclose(row["mean"], 5 * flux_unit)
    assert_quantity_allclose(row["slice_wave"], 4.894499866699333 * u.um)

    # Move slider and make sure it recomputes for a new slice automatically.
    cube_slice_plg = cubeviz_helper.plugins["Slice"]._obj
    cube_slice_plg.vue_goto_first()
    plg.vue_do_aper_phot()
    row = cubeviz_helper.get_aperture_photometry_results()[1]

    # Same rectangle but different slice value.
    assert_allclose(row["xcenter"], 1 * u.pix)
    assert_allclose(row["ycenter"], 2 * u.pix)
    sky = row["sky_center"]
    assert_allclose(sky.ra.deg, 205.43985906934287)
    assert_allclose(sky.dec.deg, 27.003490103642033)
    assert_allclose(row["sum"], 15 * flux_unit)  # 3 (w) x 5 (h) x 1 (v)
    assert_allclose(row["sum_aper_area"], 15 * (u.pix * u.pix))  # 3 (w) x 5 (h)
    assert_allclose(row["mean"], 1 * flux_unit)
    assert_quantity_allclose(row["slice_wave"], 4.8904998665093435 * u.um)

    # We continue on with test_cubeviz_aperphot_generated_2d_collapse here
    # because we want to make sure the result would append properly between 3D and 2D.
    collapse_plg = cubeviz_helper.plugins["Collapse"]._obj
    collapse_plg.vue_collapse()

    # Need this to make it available for photometry data drop-down.
    cubeviz_helper.app.add_data_to_viewer("uncert-viewer", "test[FLUX] collapsed")

    plg = cubeviz_helper.plugins["Aperture Photometry"]._obj
    plg.dataset_selected = "test[FLUX] collapsed"
    plg.aperture_selected = "Subset 1"
    plg.vue_do_aper_phot()
    row = cubeviz_helper.get_aperture_photometry_results()[2]

    # Basically, we should recover the input rectangle here.
    assert_allclose(row["xcenter"], 1 * u.pix)
    assert_allclose(row["ycenter"], 2 * u.pix)
    sky = row["sky_center"]
    assert_allclose(sky.ra.deg, 205.43985906934287)
    assert_allclose(sky.dec.deg, 27.003490103642033)
    assert_allclose(row["sum"], 540 * flux_unit)  # 3 (w) x 5 (h) x 36 (v)
    assert_allclose(row["sum_aper_area"], 15 * (u.pix * u.pix))  # 3 (w) x 5 (h)
    assert_allclose(row["mean"], 36 * flux_unit)
    assert np.isnan(row["slice_wave"])


def test_cubeviz_aperphot_generated_2d_moment(cubeviz_helper, image_cube_hdu_obj_microns):
    cubeviz_helper.load_data(image_cube_hdu_obj_microns, data_label="test")
    flux_unit = u.Unit("1E-17 erg*s^-1*cm^-2*Angstrom^-1")

    moment_plg = cubeviz_helper.plugins["Moment Maps"]
    _ = moment_plg.calculate_moment()

    # Need this to make it available for photometry data drop-down.
    cubeviz_helper.app.add_data_to_viewer("uncert-viewer", "test[FLUX] moment 0")

    aper = RectanglePixelRegion(center=PixCoord(x=1, y=2), width=3, height=5)
    cubeviz_helper.load_regions(aper)

    plg = cubeviz_helper.plugins["Aperture Photometry"]._obj
    plg.dataset_selected = "test[FLUX] moment 0"
    plg.aperture_selected = "Subset 1"
    plg.vue_do_aper_phot()
    row = cubeviz_helper.get_aperture_photometry_results()[0]

    # Basically, we should recover the input rectangle here.
    assert_allclose(row["xcenter"], 1 * u.pix)
    assert_allclose(row["ycenter"], 2 * u.pix)
    sky = row["sky_center"]
    assert_allclose(sky.ra.deg, 205.43985906934287)
    assert_allclose(sky.dec.deg, 27.003490103642033)
    assert_allclose(row["sum"], 540 * flux_unit)  # 3 (w) x 5 (h) x 36 (v)
    assert_allclose(row["sum_aper_area"], 15 * (u.pix * u.pix))  # 3 (w) x 5 (h)
    assert_allclose(row["mean"], 36 * flux_unit)
    assert np.isnan(row["slice_wave"])

    # Moment 1 has no compatible unit, so should not be available for photometry.
    moment_plg.n_moment = 1
    moment_plg.reference_wavelength = 5
    _ = moment_plg.calculate_moment()
    m1_lbl = "test[FLUX] moment 1"
    cubeviz_helper.app.add_data_to_viewer("uncert-viewer", m1_lbl)
    assert (m1_lbl in cubeviz_helper.app.data_collection.labels and
            m1_lbl not in plg.dataset.choices)


def test_cubeviz_aperphot_generated_3d_gaussian_smooth(cubeviz_helper, image_cube_hdu_obj_microns):
    cubeviz_helper.load_data(image_cube_hdu_obj_microns, data_label="test")
    flux_unit = u.Unit("1E-17 erg*s^-1*cm^-2*Angstrom^-1")

    gauss_plg = cubeviz_helper.plugins["Gaussian Smooth"]._obj
    gauss_plg.mode_selected = "Spatial"
    with pytest.warns(AstropyUserWarning, match="The following attributes were set on the data"):
        _ = gauss_plg.smooth()

    # Need this to make it available for photometry data drop-down.
    cubeviz_helper.app.add_data_to_viewer("uncert-viewer", "test[FLUX] spatial-smooth stddev-1.0")

    aper = RectanglePixelRegion(center=PixCoord(x=1, y=2), width=3, height=5)
    cubeviz_helper.load_regions(aper)

    plg = cubeviz_helper.plugins["Aperture Photometry"]._obj
    plg.dataset_selected = "test[FLUX] spatial-smooth stddev-1.0"
    plg.aperture_selected = "Subset 1"
    plg.vue_do_aper_phot()
    row = cubeviz_helper.get_aperture_photometry_results()[0]

    # Basically, we should recover the input rectangle here.
    assert_allclose(row["xcenter"], 1 * u.pix)
    assert_allclose(row["ycenter"], 2 * u.pix)
    sky = row["sky_center"]
    assert_allclose(sky.ra.deg, 205.43985906934287)
    assert_allclose(sky.dec.deg, 27.003490103642033)
    assert_allclose(row["sum"], 48.54973 * flux_unit)  # 3 (w) x 5 (h) x <5 (v)
    assert_allclose(row["sum_aper_area"], 15 * (u.pix * u.pix))  # 3 (w) x 5 (h)
    assert_allclose(row["mean"], 3.236648941040039 * flux_unit)
    assert_quantity_allclose(row["slice_wave"], 4.894499866699333 * u.um)


def test_cubeviz_aperphot_cube_orig_flux_mjysr(cubeviz_helper, spectrum1d_cube_custom_fluxunit):
    cube = spectrum1d_cube_custom_fluxunit(fluxunit=u.MJy / u.sr)
    cubeviz_helper.load_data(cube, data_label="test")

    aper = RectanglePixelRegion(center=PixCoord(x=1, y=3), width=1, height=1)
    bg = RectanglePixelRegion(center=PixCoord(x=0, y=2), width=1, height=1)
    cubeviz_helper.load_regions([aper, bg])

    plg = cubeviz_helper.plugins["Aperture Photometry"]._obj
    plg.dataset_selected = "test[FLUX]"
    plg.aperture_selected = "Subset 1"
    plg.background_selected = "Subset 2"

    # Make sure per steradian is handled properly.
    assert_allclose(plg.pixel_area, 0.01)
    assert_allclose(plg.flux_scaling, 0.003631)

    plg.vue_do_aper_phot()
    row = cubeviz_helper.get_aperture_photometry_results()[0]

    # Basically, we should recover the input rectangle here, minus background.
    assert_allclose(row["xcenter"], 1 * u.pix)
    assert_allclose(row["ycenter"], 3 * u.pix)
    assert_allclose(row["sum"], 1.1752215e-12 * u.MJy)  # (15 - 10) MJy/sr x 2.3504431e-13 sr
    assert_allclose(row["sum_aper_area"], 1 * (u.pix * u.pix))
    assert_allclose(row["pixarea_tot"], 2.350443053909789e-13 * u.sr)
    assert_allclose(row["aperture_sum_mag"], 23.72476627732448 * u.mag)
    assert_allclose(row["mean"], 5 * (u.MJy / u.sr))
    # TODO: check if slice plugin has value_unit set correctly
    assert_quantity_allclose(row["slice_wave"], 0.46236 * u.um)
