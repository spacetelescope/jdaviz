import numpy as np
import pytest
from astropy import units as u
from astropy.nddata import InverseVariance
from specutils import Spectrum1D

from jdaviz.core.custom_units_and_equivs import SPEC_PHOTON_FLUX_DENSITY_UNITS


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


@pytest.mark.parametrize("flux_unit, expected_choices", [(u.count, ['ct']),
                                                         (u.Jy, SPEC_PHOTON_FLUX_DENSITY_UNITS),
                                                         (u.nJy, SPEC_PHOTON_FLUX_DENSITY_UNITS + ['nJy'])])  # noqa
def test_flux_unit_choices(specviz_helper, flux_unit, expected_choices):
    """
    Test that cubes loaded with various flux units have the expected default
    flux unit selection in the unit conversion plugin, and that the list of
    convertable flux units in the dropdown is correct.
    """

    spec = Spectrum1D([1, 2, 3] * flux_unit, [4, 5, 6] * u.um)
    specviz_helper.load_data(spec)

    uc_plg = specviz_helper.plugins['Unit Conversion']

    assert uc_plg.flux_unit.selected == flux_unit.to_string()
    assert uc_plg.flux_unit.choices == expected_choices


def test_mosviz_profile_view_mouseover(specviz2d_helper):
    data = np.zeros((5, 10))
    data[3] = np.arange(10)
    spectrum2d = Spectrum1D(flux=data*u.MJy, spectral_axis=data[3]*u.um)

    specviz2d_helper.load_data(spectrum2d)
    viewer = specviz2d_helper.app.get_viewer("spectrum-viewer")
    plg = specviz2d_helper.plugins["Unit Conversion"]

    # make sure we don't expose angle, sb, nor spectral-y units when native
    # units are in flux
    assert hasattr(plg, 'flux_unit')
    assert not hasattr(plg, 'angle_unit')
    assert not hasattr(plg, 'sb_unit')
    assert not hasattr(plg, 'spectral_y_type')

    label_mouseover = specviz2d_helper.app.session.application._tools['g-coords-info']
    label_mouseover._viewer_mouse_event(viewer,
                                        {'event': 'mousemove',
                                         'domain': {'x': 5, 'y': 3}})

    assert label_mouseover.as_text() == ('Cursor 5.00000e+00, 3.00000e+00',
                                         'Wave 5.00000e+00 um (5 pix)',
                                         'Flux 5.00000e+00 MJy')

    plg._obj.flux_unit_selected = 'Jy'
    assert label_mouseover.as_text() == ('Cursor 5.00000e+00, 3.00000e+00',
                                         'Wave 5.00000e+00 um (5 pix)',
                                         'Flux 5.00000e+06 Jy')

    # test mouseover when spectral density equivalencies are required for conversion
    plg._obj.flux_unit_selected = 'erg / (Angstrom s cm2)'
    assert label_mouseover.as_text() == ('Cursor 5.00000e+00, 3.00000e+00',
                                         'Wave 5.00000e+00 um (5 pix)',
                                         'Flux 5.99585e-08 erg / (Angstrom s cm2)')
