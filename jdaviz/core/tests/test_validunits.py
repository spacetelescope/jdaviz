import astropy.units as u
import pytest

from jdaviz.core.validunits import check_if_unit_is_per_solid_angle


@pytest.mark.parametrize("unit, is_solid_angle", [
    ('erg / sr', True), ('erg / (deg * deg)', True), ('erg / (deg * arcsec)', True),
    ('erg / (deg**2)', True), ('erg deg**-2', True), ('erg sr^-1', True),
    ('erg / degree', False), ('erg sr^-2', False)])
def test_check_if_unit_is_per_solid_angle(unit, is_solid_angle):
    # test function that tests if a unit string or u.Unit is per solid angle
    assert check_if_unit_is_per_solid_angle(unit) == is_solid_angle

    # turn string into u.Unit, and make sure it also passes
    assert check_if_unit_is_per_solid_angle(u.Unit(unit)) == is_solid_angle
