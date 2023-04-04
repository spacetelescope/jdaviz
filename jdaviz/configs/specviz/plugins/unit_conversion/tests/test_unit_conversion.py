import pytest
from astropy import units as u


# On failure, should not crash; essentially a no-op.
@pytest.mark.parametrize(
    ('new_spectral_axis', 'new_flux', 'expected_spectral_axis', 'expected_flux'),
    [("fail", "erg / (s cm2 Angstrom)", "Angstrom", "erg / (s cm2 Angstrom)"),
     ("None", "fail", "Angstrom", "Jy"),
     ("micron", "fail", "micron", "Jy")])
def test_value_error_exception(specviz_helper, spectrum1d, new_spectral_axis, new_flux,
                               expected_spectral_axis, expected_flux):
    specviz_helper.load_spectrum(spectrum1d, data_label="Test 1D Spectrum")
    viewer = specviz_helper.app.get_viewer("spectrum-viewer")
    plg = specviz_helper.plugins["Unit Conversion"]

    try:
        plg.spectral_unit = new_spectral_axis
    except ValueError as e:
        if "reverting selection to" not in repr(e):
            raise
    try:
        plg.flux_unit = new_flux
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
    specviz_helper.load_spectrum(spectrum1d, data_label="Test 1D Spectrum")

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
    specviz_helper.load_spectrum(spectrum1d, data_label="Test 1D Spectrum")

    viewer = specviz_helper.app.get_viewer("spectrum-viewer")
    plg = specviz_helper.plugins["Unit Conversion"]
    new_flux = "erg / (s cm2 Angstrom)"
    plg.flux_unit = new_flux

    assert len(specviz_helper.app.data_collection) == 1
    assert u.Unit(viewer.state.x_display_unit) == u.Unit('Angstrom')
    assert u.Unit(viewer.state.y_display_unit) == u.Unit(new_flux)


@pytest.mark.parametrize('uncert', (False, True))
def test_conv_wave_flux(specviz_helper, spectrum1d, uncert):
    if uncert is False:
        spectrum1d.uncertainty = None
    specviz_helper.load_spectrum(spectrum1d, data_label="Test 1D Spectrum")

    viewer = specviz_helper.app.get_viewer("spectrum-viewer")
    plg = specviz_helper.plugins["Unit Conversion"]
    new_spectral_axis = "micron"
    new_flux = "erg / (s cm2 Angstrom)"
    plg.spectral_unit = new_spectral_axis
    plg.flux_unit = new_flux

    assert len(specviz_helper.app.data_collection) == 1
    assert u.Unit(viewer.state.x_display_unit) == u.Unit(new_spectral_axis)
    assert u.Unit(viewer.state.y_display_unit) == u.Unit(new_flux)


def test_conv_no_data(specviz_helper):
    """plugin unit selections won't have valid choices yet, preventing
    attempting to set display units."""
    plg = specviz_helper.plugins["Unit Conversion"]
    with pytest.raises(ValueError, match="no valid unit choices"):
        plg.spectral_unit = "micron"
    with pytest.raises(ValueError, match="no valid unit choices"):
        plg.flux_unit = "erg / (s cm2 Angstrom)"
    assert len(specviz_helper.app.data_collection) == 0
