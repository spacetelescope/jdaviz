import pytest


# On failure, should not crash; essentially a no-op.
@pytest.mark.parametrize(
    ('new_spectral_axis', 'new_flux', 'expected_spectral_axis', 'expected_flux'),
    [("fail", "erg / (s cm2 um)", "Angstrom", "erg / (s cm2 um)"),
     ("None", "fail", "Angstrom", "Jy"),
     ("micron", "fail", "micron", "Jy")])
def test_value_error_exception(specviz_helper, spectrum1d, new_spectral_axis, new_flux,
                               expected_spectral_axis, expected_flux):
    specviz_helper.load_spectrum(spectrum1d, data_label="Test 1D Spectrum")
    viewer = specviz_helper.app.get_viewer("spectrum-viewer")
    plg = specviz_helper.plugins["Unit Conversion"]._obj

    plg.new_spectral_axis_unit = new_spectral_axis
    plg.new_flux_unit = new_flux
    plg.vue_unit_conversion()

    assert len(specviz_helper.app.data_collection) == 1
    assert viewer.state.x_display_unit == expected_spectral_axis
    assert viewer.state.y_display_unit == expected_flux


@pytest.mark.parametrize('uncert', (False, True))
def test_conv_wave_only(specviz_helper, spectrum1d, uncert):
    if uncert is False:
        spectrum1d.uncertainty = None
    specviz_helper.load_spectrum(spectrum1d, data_label="Test 1D Spectrum")

    viewer = specviz_helper.app.get_viewer("spectrum-viewer")
    plg = specviz_helper.plugins["Unit Conversion"]._obj
    new_spectral_axis = "micron"
    plg.new_spectral_axis_unit = new_spectral_axis
    plg.vue_unit_conversion()

    assert len(specviz_helper.app.data_collection) == 1
    assert viewer.state.x_display_unit == new_spectral_axis
    assert viewer.state.y_display_unit == 'Jy'


@pytest.mark.parametrize('uncert', (False, True))
def test_conv_flux_only(specviz_helper, spectrum1d, uncert):
    if uncert is False:
        spectrum1d.uncertainty = None
    specviz_helper.load_spectrum(spectrum1d, data_label="Test 1D Spectrum")

    viewer = specviz_helper.app.get_viewer("spectrum-viewer")
    plg = specviz_helper.plugins["Unit Conversion"]._obj
    new_flux = "erg / (s cm2 um)"
    plg.new_flux_unit = new_flux
    plg.vue_unit_conversion()

    assert len(specviz_helper.app.data_collection) == 1
    assert viewer.state.x_display_unit == 'Angstrom'
    assert viewer.state.y_display_unit == new_flux


@pytest.mark.parametrize('uncert', (False, True))
def test_conv_wave_flux(specviz_helper, spectrum1d, uncert):
    if uncert is False:
        spectrum1d.uncertainty = None
    specviz_helper.load_spectrum(spectrum1d, data_label="Test 1D Spectrum")

    viewer = specviz_helper.app.get_viewer("spectrum-viewer")
    plg = specviz_helper.plugins["Unit Conversion"]._obj
    new_spectral_axis = "micron"
    new_flux = "erg / (s cm2 um)"
    plg.new_spectral_axis_unit = new_spectral_axis
    plg.new_flux_unit = new_flux
    plg.vue_unit_conversion()

    assert len(specviz_helper.app.data_collection) == 1
    assert viewer.state.x_display_unit == new_spectral_axis
    assert viewer.state.y_display_unit == new_flux


def test_conv_no_data(specviz_helper):
    """Should not crash."""
    plg = specviz_helper.plugins["Unit Conversion"]._obj
    plg.new_spectral_axis_unit = "micron"
    plg.new_flux_unit = "erg / (s cm2 um)"
    plg.vue_unit_conversion()
    assert len(specviz_helper.app.data_collection) == 0
