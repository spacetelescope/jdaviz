import numpy as np
import pytest
from astropy import units as u
from astropy.table import Table
from astropy.tests.helper import assert_quantity_allclose
from astropy.utils.exceptions import AstropyUserWarning
from numpy.testing import assert_allclose
from regions import RectanglePixelRegion, PixCoord

from jdaviz.core.custom_units_and_equivs import PIX2, SPEC_PHOTON_FLUX_DENSITY_UNITS
from jdaviz.core.unit_conversion_utils import (flux_conversion_general,
                                               handle_squared_flux_unit_conversions)


def test_cubeviz_aperphot_cube_orig_flux(cubeviz_helper, image_cube_hdu_obj_microns):
    cubeviz_helper.load_data(image_cube_hdu_obj_microns, data_label="test")
    flux_unit = u.Unit("1E-17 erg*s^-1*cm^-2*Angstrom^-1*pix^-2")
    solid_angle_unit = PIX2

    aper = RectanglePixelRegion(center=PixCoord(x=1, y=2), width=3, height=5)

    cubeviz_helper.plugins['Subset Tools'].import_region(aper)

    # Make sure MASK is not an option even when shown in viewer.
    cubeviz_helper.app.add_data_to_viewer("flux-viewer", "test[MASK]", visible=True)

    plg = cubeviz_helper.plugins["Aperture Photometry"]._obj
    assert plg.dataset.labels == ["test[FLUX]", "test[ERR]"]
    assert plg.cube_slice == "4.894e+00 um"

    plg.dataset_selected = "test[FLUX]"
    plg.aperture_selected = "Subset 1"
    plg.vue_do_aper_phot()
    row = plg.export_table()[0]

    # Basically, we should recover the input rectangle here.
    assert_allclose(row["xcenter"], 1 * u.pix)
    assert_allclose(row["ycenter"], 2 * u.pix)
    sky = row["sky_center"]
    assert_allclose(sky.ra.deg, 205.43985906934287)
    assert_allclose(sky.dec.deg, 27.003490103642033)

    # sum should be in flux ( have factor of pix^2 multiplied out of input unit)
    assert_allclose(row["sum"], 75 * flux_unit * solid_angle_unit)  # 3 (w) x 5 (h) x 5 (v)

    assert_allclose(row["sum_aper_area"], 15 * solid_angle_unit)  # 3 (w) x 5 (h)
    assert_allclose(row["mean"], 5 * flux_unit)
    assert_quantity_allclose(row["slice_wave"], 4.894499866699333 * u.um)

    # Move slider and make sure it recomputes for a new slice automatically.
    cube_slice_plg = cubeviz_helper.plugins["Slice"]._obj
    cube_slice_plg.vue_goto_first()
    plg.vue_do_aper_phot()
    row = plg.export_table()[1]

    # Same rectangle but different slice value.
    assert_allclose(row["xcenter"], 1 * u.pix)
    assert_allclose(row["ycenter"], 2 * u.pix)
    sky = row["sky_center"]
    assert_allclose(sky.ra.deg, 205.43985906934287)
    assert_allclose(sky.dec.deg, 27.003490103642033)

    # sum should be in flux ( have factor of pix^2 multiplied out of input unit)
    assert_allclose(row["sum"], 15 * flux_unit * solid_angle_unit)  # 3 (w) x 5 (h) x 1 (v)

    assert_allclose(row["sum_aper_area"], 15 * solid_angle_unit)  # 3 (w) x 5 (h)
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
    row = plg.export_table()[2]

    # Basically, we should recover the input rectangle here.
    assert_allclose(row["xcenter"], 1 * u.pix)
    assert_allclose(row["ycenter"], 2 * u.pix)
    sky = row["sky_center"]
    assert_allclose(sky.ra.deg, 205.43985906934287)
    assert_allclose(sky.dec.deg, 27.003490103642033)

    # sum should be in flux ( have factor of pix^2 multiplied out of input unit)
    assert_allclose(row["sum"], 540 * flux_unit * solid_angle_unit)  # 3 (w) x 5 (h) x 36 (v)

    assert_allclose(row["sum_aper_area"], 15 * solid_angle_unit)  # 3 (w) x 5 (h)
    assert_allclose(row["mean"], 36 * flux_unit)
    assert np.isnan(row["slice_wave"])

    # Invalid counts conversion factor
    plg.counts_factor = -1
    plg.vue_do_aper_phot()
    assert "cannot be negative" in plg.result_failed_msg


def test_cubeviz_aperphot_generated_3d_gaussian_smooth(cubeviz_helper, image_cube_hdu_obj_microns):
    cubeviz_helper.load_data(image_cube_hdu_obj_microns, data_label="test")
    flux_unit = u.Unit("1E-17 erg*s^-1*cm^-2*Angstrom^-1*pix^-2")  # actually a sb
    solid_angle_unit = PIX2

    gauss_plg = cubeviz_helper.plugins["Gaussian Smooth"]._obj
    gauss_plg.mode_selected = "Spatial"
    with pytest.warns(AstropyUserWarning, match="The following attributes were set on the data"):
        _ = gauss_plg.smooth()

    # Need this to make it available for photometry data drop-down.
    cubeviz_helper.app.add_data_to_viewer("uncert-viewer", "test[FLUX] spatial-smooth stddev-1.0")

    aper = RectanglePixelRegion(center=PixCoord(x=1, y=2), width=3, height=5)
    cubeviz_helper.plugins['Subset Tools'].import_region(aper)

    plg = cubeviz_helper.plugins["Aperture Photometry"]._obj
    plg.dataset_selected = "test[FLUX] spatial-smooth stddev-1.0"
    plg.aperture_selected = "Subset 1"
    plg.vue_do_aper_phot()
    row = cubeviz_helper.plugins['Aperture Photometry'].export_table()[0]

    # Basically, we should recover the input rectangle here.
    assert_allclose(row["xcenter"], 1 * u.pix)
    assert_allclose(row["ycenter"], 2 * u.pix)
    sky = row["sky_center"]
    assert_allclose(sky.ra.deg, 205.43985906934287)
    assert_allclose(sky.dec.deg, 27.003490103642033)

    # sum should be in flux ( have factor of pix^2 multiplied out of input unit)
    assert_allclose(row["sum"], 48.54973 * flux_unit * solid_angle_unit)  # 3 (w) x 5 (h) x <5 (v)

    assert_allclose(row["sum_aper_area"], 15 * solid_angle_unit)  # 3 (w) x 5 (h)
    assert_allclose(row["mean"], 3.236648941040039 * flux_unit)
    assert_quantity_allclose(row["slice_wave"], 4.894499866699333 * u.um)


@pytest.mark.parametrize("cube_unit", [u.MJy / u.sr, u.MJy, u.MJy / PIX2])
def test_cubeviz_aperphot_cube_sr_and_pix2(cubeviz_helper,
                                           spectrum1d_cube_custom_fluxunit,
                                           cube_unit):
    # tests aperture photometry outputs between different inputs of flux (which
    # should be converted to a surface brighntess after loading), flux per sr
    # and flux per square pixel. the pixel area for per steradian cubes is
    # set so the output values between units will be the same

    cube = spectrum1d_cube_custom_fluxunit(fluxunit=cube_unit)
    cubeviz_helper.load_data(cube, data_label="test")

    aper = RectanglePixelRegion(center=PixCoord(x=3, y=1), width=1, height=1)
    bg = RectanglePixelRegion(center=PixCoord(x=2, y=0), width=1, height=1)
    cubeviz_helper.plugins['Subset Tools'].import_region(
        [aper, bg], combination_mode='new')

    plg = cubeviz_helper.plugins["Aperture Photometry"]._obj
    plg.dataset_selected = "test[FLUX]"
    plg.aperture_selected = "Subset 1"
    plg.background_selected = "Subset 2"

    #  Check that the default flux scaling is present for MJy / sr cubes
    if cube_unit == (u.MJy / u.sr):
        assert_allclose(plg.flux_scaling, 0.003631)
    else:
        assert_allclose(plg.flux_scaling, 0.0)

    # if cube is MJy / sr, set pixel area to 1 sr / pix2 so
    # we can directly compare outputs between per sr and per pixel cubes, which
    # will give the same results with this scaling
    if cube_unit == (u.MJy / u.sr):
        assert_allclose(plg.pixel_area, 0.01)  # check default
        plg.pixel_area = 1 * (u.sr).to(u.arcsec*u.arcsec)
        solid_angle_unit = u.sr

    else:
        # for per pixel cubes, set flux scaling to default for MJy / sr cubes
        # so we can directly compare. this shouldn't be populated automatically,
        # which is checked above
        plg.flux_scaling = 0.003631
        solid_angle_unit = PIX2
        cube_unit = u.MJy / solid_angle_unit  # cube unit in app is now per pix2

    plg.vue_do_aper_phot()
    row = cubeviz_helper.plugins['Aperture Photometry'].export_table()[0]

    # Basically, we should recover the input rectangle here, minus background.
    assert_allclose(row["xcenter"], 3 * u.pix)
    assert_allclose(row["ycenter"], 1 * u.pix)
    # (15 - 10) MJy/sr x 1 sr, will always be MJy since solid angle is multiplied out
    assert_allclose(row["sum"], 5.0 * u.MJy)

    assert_allclose(row["sum_aper_area"], 1 * PIX2)

    #  we forced area to be one sr so MJy / sr and MJy / pix2 gave the same result
    assert_allclose(row["pixarea_tot"], 1.0 * solid_angle_unit)

    # also forced flux_scaling to be the same for MJy / sr cubes, which get a
    # default value populated, and MJy / pix2 which have a default of 0.0
    assert_allclose(row["aperture_sum_mag"], -7.847359 * u.mag)

    assert_allclose(row["mean"], 5 * (cube_unit))
    # TODO: check if slice plugin has value_unit set correctly
    assert_quantity_allclose(row["slice_wave"], 0.46236 * u.um)


def test_cubeviz_aperphot_cube_orig_flux_mjysr(cubeviz_helper,
                                               spectrum1d_cube_custom_fluxunit):
    # this test is essentially the same as test_cubeviz_aperphot_cube_sr_and_pix2
    # but for a single surface brightness unit and without changing the pixel
    # area to make outputs the same. it was requested in review to keep both tests
    cube = spectrum1d_cube_custom_fluxunit(fluxunit=u.MJy / u.sr)
    cubeviz_helper.load_data(cube, data_label="test")

    aper = RectanglePixelRegion(center=PixCoord(x=3, y=1), width=1, height=1)
    bg = RectanglePixelRegion(center=PixCoord(x=2, y=0), width=1, height=1)
    cubeviz_helper.plugins['Subset Tools'].import_region([aper, bg],
                                                         combination_mode='new')

    plg = cubeviz_helper.plugins["Aperture Photometry"]._obj
    plg.dataset_selected = "test[FLUX]"
    plg.aperture_selected = "Subset 1"
    plg.background_selected = "Subset 2"

    # Make sure per steradian is handled properly.
    assert_allclose(plg.pixel_area, 0.01)
    assert_allclose(plg.flux_scaling, 0.003631)

    plg.vue_do_aper_phot()
    row = cubeviz_helper.plugins['Aperture Photometry'].export_table()[0]

    # Basically, we should recover the input rectangle here, minus background.
    assert_allclose(row["xcenter"], 3 * u.pix)
    assert_allclose(row["ycenter"], 1 * u.pix)
    assert_allclose(row["sum"], 1.1752215e-12 * u.MJy)  # (15 - 10) MJy/sr x 2.3504431e-13 sr
    assert_allclose(row["sum_aper_area"], 1 * PIX2)
    assert_allclose(row["pixarea_tot"], 2.350443053909789e-13 * u.sr)
    assert_allclose(row["aperture_sum_mag"], 23.72476627732448 * u.mag)
    assert_allclose(row["mean"], 5 * (u.MJy / u.sr))
    # TODO: check if slice plugin has value_unit set correctly
    assert_quantity_allclose(row["slice_wave"], 0.46236 * u.um)


def _compare_table_units(orig_tab, new_tab, orig_flux_unit=None,
                         new_flux_unit=None, equivalencies=None):

    # compare two photometry tables with different units row by row, and make
    # sure that the units are as expected, and that they are equivalent once
    # translated

    for i, row in enumerate(orig_tab):
        new_unit = new_tab[i]['unit'] or '-'
        orig_unit = row['unit'] or '-'
        if new_unit != '-' and orig_unit != '-':

            new_unit = u.Unit(new_unit)
            new = float(new_tab[i]['result']) * new_unit

            orig_unit = u.Unit(orig_unit)
            orig = float(row['result']) * orig_unit

            if 'var' in row['function']:  # variance is in units of flux/sb squared
                orig_converted = handle_squared_flux_unit_conversions(orig.value,
                                                                      orig_unit,
                                                                      new_unit,
                                                                      equivalencies)
            else:
                orig_converted = flux_conversion_general(orig.value,
                                                         orig_unit,
                                                         new_unit,
                                                         equivalencies)

            # low rtol for match, phot table is rounded
            assert_quantity_allclose(orig_converted, new, rtol=1e-03)


@pytest.mark.slow
@pytest.mark.parametrize("flux_unit", [u.Unit(x) for x in SPEC_PHOTON_FLUX_DENSITY_UNITS])
@pytest.mark.parametrize("angle_unit", [u.sr, PIX2])
@pytest.mark.parametrize("new_flux_unit", [u.Unit(x) for x in SPEC_PHOTON_FLUX_DENSITY_UNITS])
def test_cubeviz_aperphot_unit_conversions(cubeviz_helper,
                                           spectrum1d_cube_custom_fluxunit,
                                           flux_unit, angle_unit, new_flux_unit):
    """
    Test cubeviz aperture photometry with all possible unit conversions for
    cubes in spectral/photon surface brightness units (e.g. Jy/sr, Jy/pix2).

    The aperture photometry plugin should respect the choice of flux and angle
    unit selected in the Unit Conversion plugin, and inputs and results should
    be converted based on selection. All conversions between units in the
    flux dropdown menu in the unit conversion plugin should be supported
    by aperture photometry.
    """

    if new_flux_unit == flux_unit:  # skip 'converting' to same unit
        return

    cube_unit = flux_unit / angle_unit

    # get strings of input units
    flux_unit_str = flux_unit.to_string()
    angle_unit_str = angle_unit.to_string()
    cube_unit_str = cube_unit.to_string()
    new_flux_unit_str = new_flux_unit.to_string()

    # load cube with specified unit
    cube = spectrum1d_cube_custom_fluxunit(fluxunit=cube_unit, shape=(5, 5, 4),
                                           with_uncerts=True)
    cubeviz_helper.load_data(cube, data_label="test")

    # get plugins
    st = cubeviz_helper.plugins['Subset Tools']
    ap = cubeviz_helper.plugins['Aperture Photometry']._obj
    uc = cubeviz_helper.plugins['Unit Conversion']

    # load aperture
    aper = RectanglePixelRegion(center=PixCoord(x=2, y=3), width=1, height=1)
    st.import_region(aper, combination_mode='new')

    # select dataset and aperture in plugin
    ap.dataset_selected = "test[FLUX]"
    ap.aperture_selected = "Subset 1"

    # equivalencies for unit conversion, we only need u.spectral_density because
    # no flux<>sb conversions will occur in this plugin
    equiv = u.spectral_density(ap._cube_wave)

    # check initial unit traitlets are synced between ap. phot and unit conv. plugins
    assert uc.flux_unit.selected == ap.flux_scaling_display_unit == flux_unit_str
    assert uc.angle_unit.selected == angle_unit_str
    assert ap.display_unit == cube_unit_str
    assert ap.flux_scaling_display_unit == flux_unit_str

    # set background to manual and background/flux scaling to 1 to make it
    # easier to compare between unit conversions
    ap.background_selected == 'Manual'
    ap.background_value = 1.
    ap.flux_scaling = 1.

    # do aperture photometry with inital cube units to compare original results
    # to results after flux unit conversion
    ap.vue_do_aper_phot()
    orig_tab = Table(ap.results)

    # set to new unit
    uc.flux_unit.selected = new_flux_unit_str

    # make sure display units in aperture phot plugin reflect change
    assert (u.Unit(ap.display_unit) * angle_unit).to_string() == new_flux_unit
    assert ap.flux_scaling_display_unit == new_flux_unit_str

    # make sure background and flux scaling were converted to new unit
    assert_allclose((ap.background_value * new_flux_unit).to(flux_unit, equiv).value, 1.)
    assert_allclose((ap.flux_scaling * new_flux_unit).to(flux_unit, equiv).value, 1.)

    ap.vue_do_aper_phot()
    new_tab = Table(ap.results)

    # if ap. phot silently fails, then 'new_tab' will just be the last
    # calculated one, so make sure this didn't happen
    assert not np.all(orig_tab == new_tab)

    # compare output tables row by row between original and new unit
    _compare_table_units(orig_tab, new_tab, orig_flux_unit=flux_unit,
                         new_flux_unit=new_flux_unit_str,
                         equivalencies=equiv)

    # todo: figure out how to test radial profile and curve of growth plots
    # related ticket: JDAT 4962
