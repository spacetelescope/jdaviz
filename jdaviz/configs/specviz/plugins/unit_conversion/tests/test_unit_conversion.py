import numpy as np
import pytest
from astropy import units as u
from astropy.nddata import InverseVariance
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
