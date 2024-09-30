import numpy as np
import pytest
from astropy import units as u
from astropy.nddata import InverseVariance
from astropy.wcs import WCS
from regions import PixCoord, CirclePixelRegion
from specutils import Spectrum1D


# On failure, should not crash; essentially a no-op.
@pytest.mark.parametrize(
    ('new_spectral_axis', 'new_flux', 'expected_spectral_axis', 'expected_flux'),
    [("fail", "erg / (s cm2 Angstrom)", "Angstrom", "erg / (s cm2 Angstrom)"),
     ("None", "fail", "Angstrom", "Jy"),
     ("micron", "fail", "micron", "Jy")])
def test_value_error_exception(specviz_helper, spectrum1d, new_spectral_axis, new_flux,
                               expected_spectral_axis, expected_flux):
    specviz_helper.load_data(spectrum1d, data_label="Test 1D Spectrum")
    viewer = specviz_helper.app.get_viewer("spectrum-viewer")
    plg = specviz_helper.plugins["Unit Conversion"]

    try:
        plg.spectral_unit = new_spectral_axis
    except ValueError as e:
        if "reverting selection to" not in repr(e):
            raise
    try:
        plg._obj.flux_unit_selected = new_flux
    except ValueError as e:
        if "reverting selection to" not in repr(e):
            raise

    assert len(specviz_helper.app.data_collection) == 1
    assert u.Unit(viewer.state.x_display_unit) == u.Unit(expected_spectral_axis)
    assert u.Unit(viewer.state.y_display_unit) == u.Unit(expected_flux)


def test_initialize_specviz_sb(specviz_helper, spectrum1d):
    spec_sb = Spectrum1D(spectrum1d.flux/u.sr, spectrum1d.spectral_axis)
    specviz_helper.load_data(spec_sb, data_label="Test 1D Spectrum")
    plg = specviz_helper.plugins["Unit Conversion"]
    assert plg._obj.flux_unit == "Jy"
    assert plg._obj.spectral_y_type == "Surface Brightness"
    assert plg._obj.angle_unit == "sr"


@pytest.mark.parametrize('uncert', (False, True))
def test_conv_wave_only(specviz_helper, spectrum1d, uncert):
    if uncert is False:
        spectrum1d.uncertainty = None
    specviz_helper.load_data(spectrum1d, data_label="Test 1D Spectrum")

    viewer = specviz_helper.app.get_viewer("spectrum-viewer")
    plg = specviz_helper.plugins["Unit Conversion"]
    new_spectral_axis = "micron"
    plg.spectral_unit = new_spectral_axis

    assert len(specviz_helper.app.data_collection) == 1
    assert u.Unit(viewer.state.x_display_unit) == u.Unit(new_spectral_axis)
    assert u.Unit(viewer.state.y_display_unit) == u.Unit('Jy')


@pytest.mark.parametrize('uncert', (False, True))
def test_conv_flux_only(specviz_helper, spectrum1d, uncert):
    if uncert is False:
        spectrum1d.uncertainty = None
    specviz_helper.load_data(spectrum1d, data_label="Test 1D Spectrum")

    viewer = specviz_helper.app.get_viewer("spectrum-viewer")
    plg = specviz_helper.plugins["Unit Conversion"]
    new_flux = "erg / (s cm2 Angstrom)"
    plg._obj.flux_unit_selected = new_flux

    assert len(specviz_helper.app.data_collection) == 1
    assert u.Unit(viewer.state.x_display_unit) == u.Unit('Angstrom')
    assert u.Unit(viewer.state.y_display_unit) == u.Unit(new_flux)


@pytest.mark.parametrize('uncert', (False, True))
def test_conv_wave_flux(specviz_helper, spectrum1d, uncert):
    if uncert is False:
        spectrum1d.uncertainty = None
    specviz_helper.load_data(spectrum1d, data_label="Test 1D Spectrum")

    viewer = specviz_helper.app.get_viewer("spectrum-viewer")
    plg = specviz_helper.plugins["Unit Conversion"]
    new_spectral_axis = "micron"
    new_flux = "erg / (s cm2 Angstrom)"
    plg.spectral_unit = new_spectral_axis
    plg._obj.flux_unit_selected = new_flux

    assert len(specviz_helper.app.data_collection) == 1
    assert u.Unit(viewer.state.x_display_unit) == u.Unit(new_spectral_axis)
    assert u.Unit(viewer.state.y_display_unit) == u.Unit(new_flux)


def test_conv_no_data(specviz_helper, spectrum1d):
    """plugin unit selections won't have valid choices yet, preventing
    attempting to set display units."""
    # spectrum not load is in Flux units, sb_unit and flux_unit
    # should be enabled, spectral_y_type should not be
    plg = specviz_helper.plugins["Unit Conversion"]
    with pytest.raises(ValueError, match="could not find match in valid x display units"):
        plg.spectral_unit = "micron"
    assert len(specviz_helper.app.data_collection) == 0

    specviz_helper.load_data(spectrum1d, data_label="Test 1D Spectrum")

    # make sure we don't expose translations in Specviz
    assert hasattr(plg, 'flux_unit')
    assert hasattr(plg, 'angle_unit')
    assert not hasattr(plg, 'spectral_y_type')


def test_non_stddev_uncertainty(specviz_helper):
    flux = np.ones(10) * u.Jy
    stddev = 0.1
    var = stddev ** 2
    inv_var = np.ones(len(flux)) / var
    wavelength = np.linspace(1, 5, len(flux)) * u.um
    spec = Spectrum1D(
        flux,
        uncertainty=InverseVariance(inv_var),
        spectral_axis=wavelength
    )

    specviz_helper.load_data(spec)

    po = specviz_helper.plugins['Plot Options']
    po.uncertainty_visible = True

    # check that the stddev uncertainties are drawn:
    viewer = specviz_helper.app.get_viewer('spectrum-viewer')
    np.testing.assert_allclose(
        np.abs(viewer.figure.marks[-1].y - viewer.figure.marks[-1].y.mean(0)),
        stddev
    )


def cubeviz_wcs_dict():
    # returns a WCS obj and dictionary used for cubeviz tests here
    wcs_dict = {"CTYPE1": "WAVE-LOG", "CTYPE2": "DEC--TAN", "CTYPE3": "RA---TAN",
                "CRVAL1": 4.622e-7, "CRVAL2": 27, "CRVAL3": 205,
                "CDELT1": 8e-11, "CDELT2": 0.0001, "CDELT3": -0.0001,
                "CRPIX1": 0, "CRPIX2": 0, "CRPIX3": 0, "PIXAR_SR": 8e-11}
    w = WCS(wcs_dict)
    return w, wcs_dict


@pytest.mark.parametrize("angle_unit", [u.sr, u.pix*u.pix])
def test_unit_translation(cubeviz_helper, angle_unit):
    # custom cube so PIXAR_SR is in metadata, and Flux units, and in MJy
    w, wcs_dict = cubeviz_wcs_dict()
    flux = np.zeros((30, 20, 3001), dtype=np.float32)
    flux[5:15, 1:11, :] = 1
    cube = Spectrum1D(flux=flux * u.MJy / angle_unit, wcs=w, meta=wcs_dict)
    cubeviz_helper.load_data(cube, data_label="test")

    center = PixCoord(5, 10)
    cubeviz_helper.plugins['Subset Tools']._obj.import_region(
        CirclePixelRegion(center, radius=2.5))

    uc_plg = cubeviz_helper.plugins['Unit Conversion']

    # test that the scale factor was set
    assert np.all(cubeviz_helper.app.data_collection['Spectrum (sum)'].meta['_pixel_scale_factor'] != 1)  # noqa

    # When the dropdown is displayed, this ensures the loaded
    # data collection item units will be used for translations.
    assert uc_plg._obj.spectral_y_type_selected == 'Flux'

    # accessing from get_data(use_display_units=True) should return flux-like units
    assert cubeviz_helper.app._get_display_unit('spectral_y') == u.MJy
    assert cubeviz_helper.get_data('Spectrum (sum)', use_display_units=True).unit == u.MJy

    # to have access to display units
    viewer_1d = cubeviz_helper.app.get_viewer(
        cubeviz_helper._default_spectrum_viewer_reference_name)

    # change global y-units from Flux -> Surface Brightness
    uc_plg._obj.spectral_y_type_selected = 'Surface Brightness'

    assert uc_plg._obj.spectral_y_type_selected == 'Surface Brightness'
    y_display_unit = u.Unit(viewer_1d.state.y_display_unit)

    # check if units translated
    assert y_display_unit == u.MJy / angle_unit

    # get_data(use_display_units=True) should return surface brightness-like units
    assert cubeviz_helper.app._get_display_unit('spectral_y') == u.MJy / angle_unit
    assert cubeviz_helper.get_data('Spectrum (sum)', use_display_units=True).unit == u.MJy / angle_unit  # noqa


@pytest.mark.parametrize("angle_unit", [u.sr, u.pix*u.pix])
def test_sb_unit_conversion(cubeviz_helper, angle_unit):

    angle_str = angle_unit.to_string()

    # custom cube to have Surface Brightness units
    w, wcs_dict = cubeviz_wcs_dict()
    flux = np.zeros((30, 20, 3001), dtype=np.float32)
    flux[5:15, 1:11, :] = 1
    cube = Spectrum1D(flux=flux * (u.MJy / angle_unit), wcs=w, meta=wcs_dict)
    cubeviz_helper.load_data(cube, data_label="test")

    uc_plg = cubeviz_helper.plugins['Unit Conversion']
    uc_plg.open_in_tray()

    # ensure that per solid angle cube defaults to Flux spectrum
    assert uc_plg.spectral_y_type == 'Flux'
    # flux choices is populated with flux units
    assert uc_plg.flux_unit.choices
    # and angle choices should be the only the input angle
    assert len(uc_plg.angle_unit.choices) == 1
    assert angle_str in uc_plg.angle_unit.choices

    # to have access to display units
    viewer_1d = cubeviz_helper.app.get_viewer(
        cubeviz_helper._default_spectrum_viewer_reference_name)

    uc_plg.spectral_y_type.selected = 'Surface Brightness'

    # Surface Brightness conversion
    uc_plg.flux_unit = 'Jy'
    y_display_unit = u.Unit(viewer_1d.state.y_display_unit)
    assert y_display_unit == u.Jy / angle_unit
    label_mouseover = cubeviz_helper.app.session.application._tools["g-coords-info"]
    flux_viewer = cubeviz_helper.app.get_viewer(
        cubeviz_helper._default_flux_viewer_reference_name
    )
    label_mouseover._viewer_mouse_event(
        flux_viewer, {"event": "mousemove", "domain": {"x": 10, "y": 8}}
    )
    assert label_mouseover.as_text() == (
            f"Pixel x=00010.0 y=00008.0 Value +1.00000e+06 Jy / {angle_str}",
            "World 13h39m59.7037s +27d00m03.2400s (ICRS)",
            "204.9987654313 27.0008999946 (deg)")

    # Try a second conversion
    uc_plg.flux_unit = 'W / Hz m2'

    if angle_unit == u.pix * u.pix:  # unit string order is different for pix2 vs sr
        str_unit = 'W / (Hz m2 pix2)'
    elif angle_unit == u.sr:
        str_unit = 'W / (Hz sr m2)'

    y_display_unit = u.Unit(viewer_1d.state.y_display_unit)
    assert y_display_unit == u.Unit(str_unit)

    y_display_unit = u.Unit(viewer_1d.state.y_display_unit)
    label_mouseover._viewer_mouse_event(
        flux_viewer, {"event": "mousemove", "domain": {"x": 10, "y": 8}}
    )

    assert label_mouseover.as_text() == (
            f"Pixel x=00010.0 y=00008.0 Value +1.00000e-20 {str_unit}",
            "World 13h39m59.7037s +27d00m03.2400s (ICRS)",
            "204.9987654313 27.0008999946 (deg)")

    # really a translation test, test_unit_translation loads a Flux
    # cube, this test load a Surface Brightness Cube, this ensures
    # two-way translation
    uc_plg.flux_unit = 'MJy'
    y_display_unit = u.Unit(viewer_1d.state.y_display_unit)
    label_mouseover._viewer_mouse_event(
        flux_viewer, {"event": "mousemove", "domain": {"x": 10, "y": 8}}
    )
    assert label_mouseover.as_text() == (
            f"Pixel x=00010.0 y=00008.0 Value +1.00000e+00 MJy / {angle_str}",
            "World 13h39m59.7037s +27d00m03.2400s (ICRS)",
            "204.9987654313 27.0008999946 (deg)")

    uc_plg._obj.spectral_y_type_selected = 'Flux'
    uc_plg.flux_unit = 'Jy'
    y_display_unit = u.Unit(viewer_1d.state.y_display_unit)

    assert y_display_unit == u.Jy

    la = cubeviz_helper.plugins['Line Analysis']._obj
    assert la.dataset.get_selected_spectrum(use_display_units=True)


def test_contour_unit_conversion(cubeviz_helper, spectrum1d_cube_fluxunit_jy_per_steradian):
    # custom cube to have Surface Brightness units
    cubeviz_helper.load_data(spectrum1d_cube_fluxunit_jy_per_steradian, data_label="test")

    uc_plg = cubeviz_helper.plugins['Unit Conversion']
    uc_plg.open_in_tray()

    po_plg = cubeviz_helper.plugins['Plot Options']
    # Make sure that the contour values get updated
    po_plg.contour_visible = True

    assert uc_plg.spectral_y_type == 'Flux'
    assert uc_plg.flux_unit == 'Jy'
    assert uc_plg.sb_unit == "Jy / sr"
    assert cubeviz_helper.viewers['flux-viewer']._obj.layers[0].state.attribute_display_unit == "Jy / sr"  # noqa
    assert np.allclose(po_plg.contour_max.value, 199)

    uc_plg.spectral_y_type = 'Surface Brightness'
    uc_plg.flux_unit = 'MJy'

    assert uc_plg.sb_unit == "MJy / sr"
    assert cubeviz_helper.viewers['flux-viewer']._obj.layers[0].state.attribute_display_unit == "MJy / sr"  # noqa
    assert np.allclose(po_plg.contour_max.value, 1.99e-4)


@pytest.mark.parametrize("angle_unit", [u.sr, u.pix*u.pix])
def test_cubeviz_flux_sb_translation_counts(cubeviz_helper, angle_unit):

    """
    When a cube is loaded in counts, 'count' should be the only
    available option for flux unit. The y axis can be translated
    between flux and sb. Test a flux cube which will be converted
    to ct/pix2, and a sb cube ct/sr.
    """

    angle_str = angle_unit.to_string()

    # custom cube to have Surface Brightness units
    w, wcs_dict = cubeviz_wcs_dict()
    flux = np.zeros((30, 20, 3001), dtype=np.float32)
    flux[5:15, 1:11, :] = 1
    cube = Spectrum1D(flux=flux * (u.ct / angle_unit), wcs=w, meta=wcs_dict)
    cubeviz_helper.load_data(cube, data_label="test")

    uc_plg = cubeviz_helper.plugins['Unit Conversion']
    uc_plg.open_in_tray()

    # ensure that per solid angle cube defaults to Flux spectrum
    assert uc_plg.spectral_y_type == 'Flux'
    # flux choices is populated with only one choice, counts
    assert len(uc_plg.flux_unit.choices) == 1
    assert 'ct' in uc_plg.flux_unit.choices
    # and angle choices should be the only the input angle
    assert len(uc_plg.angle_unit.choices) == 1
    assert angle_str in uc_plg.angle_unit.choices

    # to have access to display units
    viewer_1d = cubeviz_helper.app.get_viewer(
        cubeviz_helper._default_spectrum_viewer_reference_name)

    # do a spectral y axis translation from Flux to Surface Brightness
    uc_plg.spectral_y_type.selected = 'Surface Brightness'

    y_display_unit = u.Unit(viewer_1d.state.y_display_unit)
    assert y_display_unit == u.ct / angle_unit

    # and test mouseover info
    label_mouseover = cubeviz_helper.app.session.application._tools["g-coords-info"]
    flux_viewer = cubeviz_helper.app.get_viewer(
        cubeviz_helper._default_flux_viewer_reference_name
    )
    label_mouseover._viewer_mouse_event(
        flux_viewer, {"event": "mousemove", "domain": {"x": 10, "y": 8}}
    )
    assert label_mouseover.as_text() == (
            f"Pixel x=00010.0 y=00008.0 Value +1.00000e+00 ct / {angle_str}",
            "World 13h39m59.7037s +27d00m03.2400s (ICRS)",
            "204.9987654313 27.0008999946 (deg)")
