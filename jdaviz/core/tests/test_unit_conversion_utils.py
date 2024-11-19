import astropy.units as u
from itertools import combinations
import numpy as np
import pytest

from jdaviz.core.custom_units_and_equivs import PIX2, SPEC_PHOTON_FLUX_DENSITY_UNITS
from jdaviz.core.unit_conversion_utils import (all_flux_unit_conversion_equivs,
                                               check_if_unit_is_per_solid_angle,
                                               combine_flux_and_angle_units,
                                               flux_conversion_general,
                                               handle_squared_flux_unit_conversions)


@pytest.mark.parametrize("unit, is_solid_angle", [
    ('erg / sr', True), ('erg / (deg * deg)', True), ('erg / (deg * arcsec)', True),
    ('erg / (deg**2)', True), ('erg deg**-2', True), ('erg sr^-1', True),
    ('erg / degree', False), ('erg sr^-2', False)])
def test_check_if_unit_is_per_solid_angle(unit, is_solid_angle):
    # test function that tests if a unit string or u.Unit is per solid angle
    assert check_if_unit_is_per_solid_angle(unit) == is_solid_angle

    # turn string into u.Unit, and make sure it also passes
    assert check_if_unit_is_per_solid_angle(u.Unit(unit)) == is_solid_angle


def test_general_flux_conversion():
    """
    This test function tests that the `flux_conversion_general` function is able
    to convert between all available flux units in the unit conversion plugin
    for data in spectral/photon flux density (e.g Jy, erg/s/cm2/A) or surface
    brightness. `flux_conversion_general` handles special cases where flux and
    surface brightness can't be converted directly, so it is used
    in place of astropy.units.to() across the application to handle flux/sb unit
    conversions. This test ensures that all advertised conversions are supported
    and correct.

    Also tests the `handle_squared_flux_unit_conversions` function, which is used
    to convert units for the aperture photometry table.
    """

    # required equivalencies for all flux<>flux, flux<>sb, sb<>sb conversions
    equivalencies = all_flux_unit_conversion_equivs(pixar_sr=4, cube_wave=1*u.nm)

    # first test all conversions between flux units and surface brightness units
    # (per steradian). (just test that it returns without error)
    sr_sbs = combine_flux_and_angle_units(SPEC_PHOTON_FLUX_DENSITY_UNITS, u.sr)
    all_convertable_units_sr = SPEC_PHOTON_FLUX_DENSITY_UNITS + sr_sbs
    for combo in combinations(all_convertable_units_sr, 2):
        original_unit, target_unit = (u.Unit(x) for x in combo)
        converted = flux_conversion_general([1, 2, 3], original_unit,
                                            target_unit, equivalencies)
        assert len(converted) == 3

    # next test all conversions between flux and surface brightness units (per
    # square pixel), omitting the flux<>flux conversions already covered above
    pix_sbs = combine_flux_and_angle_units(SPEC_PHOTON_FLUX_DENSITY_UNITS, PIX2)
    all_convertable_units_pix = SPEC_PHOTON_FLUX_DENSITY_UNITS + pix_sbs
    all_convertable_units_pix = set(all_convertable_units_pix) - set(all_convertable_units_sr)
    for combo in combinations(all_convertable_units_pix, 2):
        original_unit, target_unit = (u.Unit(x) for x in combo)
        converted = flux_conversion_general([1, 2, 3], original_unit,
                                            target_unit, equivalencies)
        assert len(converted) == 3

    # test that a unit combination passed in without the correct equivalency
    # raises the correct error
    msg = 'Could not convert Jy / pix2 to Jy / sr with provided equivalencies.'
    with pytest.raises(u.UnitConversionError, match=msg):
        converted = flux_conversion_general([1, 2, 3], u.Jy / PIX2, u.Jy / u.sr)

    # and finally, numerically verify a subset of possible unit conversion combos
    # a case of each 'type' of conversion is covered here
    units_and_expected = [(u.Jy / u.sr, u.MJy, 4.0e-6),
                          (u.Jy, u.MJy, 1.0e-6),
                          (u.Jy, u.MJy / u.sr, 2.5e-7),
                          (u.Jy, u.MJy / PIX2, 1.0e-6),
                          (u.Jy / PIX2, u.MJy / PIX2, 1.0e-6),
                          (u.MJy, u.erg / (u.s * u.cm**2 * u.AA), 0.29979246),
                          (u.MJy / PIX2, u.erg / (u.s * u.cm**2 * u.AA), 0.29979246),
                          (u.MJy, u.erg / (u.s * u.cm**2 * u.AA * PIX2), 0.29979246),
                          (u.MJy / PIX2, u.erg / (u.s * u.cm**2 * u.AA * PIX2), 0.29979246),
                          (u.MJy / u.sr, u.erg / (u.s * u.cm**2 * u.AA * u.sr), 0.29979246),
                          (u.MJy / u.sr, u.erg / (u.s * u.cm**2 * u.AA), 1.1991698),
                          (u.MJy / u.sr, u.erg / (u.s * u.cm**2 * u.AA), 1.1991698),
                          (u.MJy, u.erg / (u.s * u.cm**2 * u.AA * u.sr), 0.07494811)]

    equivalencies = all_flux_unit_conversion_equivs(pixar_sr=4, cube_wave=1*u.nm)
    for orig, targ, truth in units_and_expected:
        converted_value = flux_conversion_general([1], orig, targ, equivalencies)
        np.testing.assert_allclose(converted_value[0].value, truth)
        assert converted_value.unit == targ

        # as a bonus, also test the function that converts squared flux units
        # (relevant in aperture photometry)
        sq = handle_squared_flux_unit_conversions(1, orig**2, targ**2, equivalencies)
        np.testing.assert_allclose(sq.value, truth**2, rtol=1e-06)
        assert sq.unit == targ ** 2
