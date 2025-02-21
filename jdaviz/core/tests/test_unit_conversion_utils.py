import astropy.units as u
from itertools import combinations
from numpy.testing import assert_allclose
import pytest
from specutils import Spectrum1D

from jdaviz.core.custom_units_and_equivs import (PIX2,
                                                 SPEC_PHOTON_FLUX_DENSITY_UNITS,
                                                 _eqv_pixar_sr)
from jdaviz.core.unit_conversion_utils import (all_flux_unit_conversion_equivs,
                                               check_if_unit_is_per_solid_angle,
                                               combine_flux_and_angle_units,
                                               flux_conversion_general,
                                               handle_squared_flux_unit_conversions,
                                               viewer_flux_conversion_equivalencies)


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
        assert_allclose(converted_value[0].value, truth)
        assert converted_value.unit == targ

        # as a bonus, also test the function that converts squared flux units
        # (relevant in aperture photometry)
        sq = handle_squared_flux_unit_conversions(1, orig**2, targ**2, equivalencies)
        assert_allclose(sq.value, truth**2, rtol=1e-06)
        assert sq.unit == targ ** 2


def test_general_flux_conversion_continuted():

    """
    This is effectivley the same test as 'test_general_flux_conversion',
    and is included to retain test coverage of a deprecated function that tested
    these specific cases, as to not remove any test coverage
    since these tests are quite fast.
    """

    # the values to be translated in every test case
    values = [10, 20, 30]

    # unit conversion equivalencies for u.spectral, and flux<>SB for all flux
    # conversions supported. Using PIXAR_SR = 0.1 for flux to SB per steradian,
    # and a spectral axis for u.spectral equivalency. depending on the conversion,
    # all of these equivs might not be required but it is harmless to pass them anyway.
    equivs = all_flux_unit_conversion_equivs(pixar_sr=0.1,
                                             cube_wave=[1, 2, 3] * u.um)

    test_combos = [(u.Jy / u.sr, u.Jy, [1, 2, 3]),
                   (u.Jy, u.Jy / u.sr, [100, 200, 300]),
                   (u.Jy / PIX2, u.Jy, [10, 20, 30]),
                   (u.Jy, u.Jy / PIX2, [10, 20, 30]),
                   (u.Jy / u.sr, u.erg / (u.Angstrom * u.s * u.cm**2 * u.sr),
                   [2.99792458e-12, 1.49896229e-12, 9.99308193e-13]),
                   (u.Jy / PIX2, u.erg / (u.Angstrom * u.s * u.cm**2 * PIX2),
                   [2.99792458e-12, 1.49896229e-12, 9.99308193e-13]),
                   (u.erg / (u.Angstrom * u.s * u.cm**2 * u.sr), u.Jy / u.sr,
                   [3.33564095e+13, 2.66851276e+14, 9.00623057e+14]),
                   (u.erg / (u.Angstrom * u.s * u.cm**2 * PIX2), u.Jy / PIX2,
                   [3.33564095e+13, 2.66851276e+14, 9.00623057e+14]),
                   (u.erg / (u.Angstrom * u.s * u.cm**2 * u.sr), u.Jy / u.sr,
                   [3.33564095e+13, 2.66851276e+14, 9.00623057e+14]),
                   (u.erg / (u.Angstrom * u.s * u.cm**2 * PIX2), u.Jy / PIX2,
                   [3.33564095e+13, 2.66851276e+14, 9.00623057e+14]),
                   (u.MJy, u.ph / (u.s * u.cm**2 * u.Hz * u.sr),
                   [0.00050341, 0.00201365, 0.0045307]),
                   (u.MJy, u.ph / (u.s * u.cm**2 * u.Hz),
                   [5.03411657e-05, 2.01364663e-04, 4.53070491e-04]),
                   (u.ph / (u.s * u.cm**2 * u.Hz * u.sr), u.MJy,
                   [198644.58571489, 198644.58571489, 198644.58571489]),
                   (u.ph / (u.s * u.cm**2 * u.Hz * PIX2), u.MJy,
                   [1986445.85714893, 1986445.85714893, 1986445.85714893]),
                   (u.Jy / u.sr, u.MJy, [1.e-06, 2.e-06, 3.e-06]),
                   (u.MJy / PIX2, u.MJy, [10, 20, 30])
                   ]

    for orig, targ, expected in test_combos:
        converted = flux_conversion_general(values, orig, targ, equivs)
        assert_allclose(converted, expected * targ, rtol=1e-05)

    # some other misc test cases from previous test
    converted = flux_conversion_general(1., u.MJy / u.sr,
                                        u.erg / (u.s * u.cm**2 * u.Hz * u.sr),
                                        equivs)
    assert_allclose(converted, 1.e-17 * u.erg / (u.s * u.cm**2 * u.Hz * u.sr))

    # another old test case
    converted = flux_conversion_general(10., u.MJy / u.sr, u.Jy / u.sr)
    assert_allclose(converted, 10000000. * u.Jy / u.sr)

    # Quantity scalar pixel scale factor
    eqv = _eqv_pixar_sr(0.1 * (u.sr / u.pix))
    assert_allclose(flux_conversion_general(values, u.Jy / u.sr, u.Jy, eqv),
                    [1, 2, 3] * u.Jy)
    assert_allclose(flux_conversion_general(values, u.Jy, u.Jy / u.sr, eqv),
                    [100, 200, 300] * u.Jy / u.sr)

    # values == 2
    assert_allclose(flux_conversion_general([10, 20], u.Jy / u.sr, u.Jy, eqv),
                    [1, 2] * u.Jy)
    assert_allclose(flux_conversion_general([10, 20], u.Jy, u.Jy / u.sr, eqv),
                    [100, 200] * u.Jy / u.sr)

    # array scale factor, same length arrays
    res = flux_conversion_general(values, u.Jy / u.sr, u.Jy,
                                  _eqv_pixar_sr([0.1, 0.2, 0.3]))
    assert_allclose(res, [1., 4., 9.] * u.Jy)

    res = flux_conversion_general(values, u.Jy, u.Jy / u.sr,
                                  _eqv_pixar_sr([0.1, 0.2, 0.3]))
    assert_allclose(res, [100, 100, 100] * u.Jy / u.sr)

    # array + quantity scale factor, same length arrays
    eqv = _eqv_pixar_sr([0.1, 0.2, 0.3] * (u.sr / u.pix))
    assert_allclose(flux_conversion_general(values, u.Jy / u.sr, u.Jy, eqv),
                    [1., 4., 9.] * u.Jy)
    assert_allclose(flux_conversion_general(values, u.Jy, u.Jy / u.sr, eqv),
                    [100, 100, 100] * u.Jy / u.sr)

    # values != 2 but _pixel_scale_factor size mismatch
    with pytest.raises(ValueError, match="operands could not be broadcast together"):
        eqv = _eqv_pixar_sr([0.1, 0.2, 0.3, 0.4])
        flux_conversion_general(values, u.Jy / u.sr, u.Jy, eqv)

    # Other kind of flux conversion unrelated to _pixel_scale_factor.
    # The answer was obtained from synphot unit conversion.
    targ = [2.99792458e-12, 1.49896229e-12, 9.99308193e-13]
    targ *= (u.erg / (u.AA * u.cm * u.cm * u.s))
    assert_allclose(flux_conversion_general(values, u.Jy, targ.unit, equivs), targ)


def test_viewer_flux_conversion():
    """
    This function tests flux/sb conversion specifically for the case of the
    spectrum viewer, where the assumption that 2 values being converted == viewer
    limits is made and the equivalencies list is determined slightly differently
    than in the general case (e.g when spectral axis length is greater that 2
    but 2 values are being converted, spectral_axis[0] is used. also if there is
    a longer list of pixel scale factors but 2 values being converted, the min/max
    of the scale factors are used.).
    """

    # use viewer_flux_conversion_equivalencies to generate list of equivalencies,
    # which requires a Spectrum1D
    spec = Spectrum1D(flux=[1, 2, 3]*u.Jy, spectral_axis=[1, 2, 3]*u.um,
                      meta={'_pixel_scale_factor': [0.1, 0.2, 0.3]})
    viewer_equivs = viewer_flux_conversion_equivalencies([10, 20], spec)

    # test for when scale factor array len > 2 but there are 2 values to be
    # converted, the min/max should be used. min_max = [0.1, 0.3]
    res = flux_conversion_general([10, 20], u.Jy / u.sr, u.Jy,
                                  viewer_equivs)
    assert_allclose(res, [1, 6] * u.Jy)
    res = flux_conversion_general([10, 20], u.Jy, u.Jy / u.sr,
                                  viewer_equivs)
    assert_allclose(res, [100, 66.66666666666667] * u.Jy / u.sr)

    # test converting 2 values when spectral axis for u.spectral,
    # contains 3 items. This will only occur in the viewer limits case, so
    values = [10, 20]
    targ = [2.99792458e-12, 5.99584916e-12]
    targ *= (u.erg / (u.AA * u.cm * u.cm * u.s))  # FLAM
    assert_allclose(flux_conversion_general(values, u.Jy, targ.unit, viewer_equivs),
                    targ)
