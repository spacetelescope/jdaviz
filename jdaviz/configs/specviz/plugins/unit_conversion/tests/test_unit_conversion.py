import pytest
import numpy as np
import astropy
from astropy import units as u
from astropy.nddata import InverseVariance
from specutils import Spectrum1D
from astropy.utils.introspection import minversion
from astropy.wcs import WCS
from regions import PixCoord, CirclePixelRegion

ASTROPY_LT_5_3 = not minversion(astropy, "5.3")


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


def test_conv_no_data(specviz_helper):
    """plugin unit selections won't have valid choices yet, preventing
    attempting to set display units."""
    plg = specviz_helper.plugins["Unit Conversion"]
    with pytest.raises(ValueError, match="no valid unit choices"):
        plg.spectral_unit = "micron"
    assert len(specviz_helper.app.data_collection) == 0


@pytest.mark.skipif(ASTROPY_LT_5_3, reason='this feature relies on astropy v5.3+')
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


def test_unit_translation(cubeviz_helper):
    # custom cube so PIXAR_SR is in metadata, and Flux units, and in MJy
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

    uc_plg = cubeviz_helper.plugins['Unit Conversion']

    # test that the scale factor was set
    assert np.all(cubeviz_helper.app.data_collection[-1].meta['_pixel_scale_factor'] != 1)

    # When the dropdown is displayed, this ensures the loaded
    # data collection item units will be used for translations.
    uc_plg._obj.show_translator = True
    assert uc_plg._obj.flux_or_sb_selected == 'Flux'

    # to have access to display units
    viewer_1d = cubeviz_helper.app.get_viewer(
        cubeviz_helper._default_spectrum_viewer_reference_name)

    # change global y-units from Flux -> Surface Brightness
    uc_plg._obj.flux_or_sb_selected = 'Surface Brightness'

    assert uc_plg._obj.flux_or_sb_selected == 'Surface Brightness'
    y_display_unit = u.Unit(viewer_1d.state.y_display_unit)

    # check if units translated
    assert y_display_unit == u.MJy / u.sr


def test_sb_unit_conversion(cubeviz_helper):
    # custom cube to have Surface Brightness units
    wcs_dict = {"CTYPE1": "WAVE-LOG", "CTYPE2": "DEC--TAN", "CTYPE3": "RA---TAN",
                "CRVAL1": 4.622e-7, "CRVAL2": 27, "CRVAL3": 205,
                "CDELT1": 8e-11, "CDELT2": 0.0001, "CDELT3": -0.0001,
                "CRPIX1": 0, "CRPIX2": 0, "CRPIX3": 0, "PIXAR_SR": 8e-11}
    w = WCS(wcs_dict)
    flux = np.zeros((30, 20, 3001), dtype=np.float32)
    flux[5:15, 1:11, :] = 1
    cube = Spectrum1D(flux=flux * (u.MJy / u.sr), wcs=w, meta=wcs_dict)
    cubeviz_helper.load_data(cube, data_label="test")

    uc_plg = cubeviz_helper.plugins['Unit Conversion']
    uc_plg.open_in_tray()

    # to have access to display units
    viewer_1d = cubeviz_helper.app.get_viewer(
        cubeviz_helper._default_spectrum_viewer_reference_name)

    uc_plg._obj.show_translator = True
    uc_plg.flux_or_sb.selected = 'Surface Brightness'

    # Surface Brightness conversion
    uc_plg.sb_unit = 'Jy / sr'
    y_display_unit = u.Unit(viewer_1d.state.y_display_unit)
    assert y_display_unit == u.Jy / u.sr

    # Try a second conversion
    uc_plg.sb_unit = 'W / Hz sr m2'
    y_display_unit = u.Unit(viewer_1d.state.y_display_unit)
    assert y_display_unit == u.Unit("W / (Hz sr m2)")

    # really a translation test, test_unit_translation loads a Flux
    # cube, this test load a Surface Brightness Cube, this ensures
    # two-way translation
    uc_plg.sb_unit = 'MJy / sr'
    y_display_unit = u.Unit(viewer_1d.state.y_display_unit)

    uc_plg._obj.show_translator = True
    uc_plg._obj.flux_or_sb_selected = 'Flux'
    uc_plg.flux_unit = 'MJy'
    y_display_unit = u.Unit(viewer_1d.state.y_display_unit)

    assert y_display_unit == u.MJy

    la = cubeviz_helper.plugins['Line Analysis']._obj
    assert la.dataset.get_selected_spectrum(use_display_units=True)
