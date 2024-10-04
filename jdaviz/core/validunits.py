from astropy import units as u
import itertools

from jdaviz.core.custom_units import PIX2, SPEC_PHOTON_FLUX_DENSITY_UNITS

__all__ = ['supported_sq_angle_units',
           'combine_flux_and_angle_units', 'units_to_strings',
           'create_spectral_equivalencies_list',
           'create_flux_equivalencies_list', 'check_if_unit_is_per_solid_angle']


def supported_sq_angle_units(as_strings=False):
    units = [PIX2, u.sr]
    if as_strings:
        units = units_to_strings(units)
    return units


def combine_flux_and_angle_units(flux_units, angle_units):
    """
    Combine (list of) flux_units and angle_units to create a list of string
    representations of surface brightness units. The returned strings will be in
    the same format as the astropy unit to_string() of the unit, for consistency.
    """
    if not isinstance(flux_units, list):
        flux_units = [flux_units]
    if not isinstance(angle_units, list):
        angle_units = [angle_units]

    return [(u.Unit(flux) / u.Unit(angle)).to_string() for flux in flux_units for angle in angle_units]  # noqa


def units_to_strings(unit_list):
    """Convert equivalencies into readable versions of the units.

    Parameters
    ----------
    unit_list : list
        List of either `astropy.units` or strings that can be converted
        to `astropy.units`.

    Returns
    -------
    result : list
        A list of the units with their best (i.e., most readable) string version.
    """
    return [u.Unit(unit).to_string() for unit in unit_list]


def create_spectral_equivalencies_list(spectral_axis_unit,
                                       exclude=[u.jupiterRad, u.earthRad, u.solRad,
                                                u.lyr, u.AU, u.pc, u.Bq, u.micron, u.lsec]):
    """Get all possible conversions from current spectral_axis_unit."""
    if spectral_axis_unit in (u.pix, u.dimensionless_unscaled):
        return [spectral_axis_unit]

    # Get unit equivalencies.
    try:
        curr_spectral_axis_unit_equivalencies = spectral_axis_unit.find_equivalent_units(
            equivalencies=u.spectral())
    except u.core.UnitConversionError:
        return []

    # Get local units.
    locally_defined_spectral_axis_units = ['Angstrom', 'nm',
                                           'um', 'Hz', 'erg']
    local_units = [u.Unit(unit) for unit in locally_defined_spectral_axis_units]

    # Remove overlap units.
    curr_spectral_axis_unit_equivalencies = list(set(curr_spectral_axis_unit_equivalencies)
                                                 - set(local_units + exclude))

    # Convert equivalencies into readable versions of the units and sorted alphabetically.
    spectral_axis_unit_equivalencies_titles = sorted(units_to_strings(
        curr_spectral_axis_unit_equivalencies))

    # Concatenate both lists with the local units coming first.
    return sorted(units_to_strings(local_units)) + spectral_axis_unit_equivalencies_titles


def create_flux_equivalencies_list(flux_unit):
    """
    Get all possible conversions for flux from flux_unit, to populate 'flux'
    dropdown menu in the unit conversion plugin.

    If flux_unit is a spectral or photon density (i.e convertable to units in
    SPEC_PHOTON_FLUX_DENSITY_UNITS), then the loaded unit and all of the
    units in SPEC_PHOTON_FLUX_DENSITY_UNITS.

    If the loaded flux unit is count, dimensionless_unscaled, DN, e/s, then
    there will be no additional items available for unit conversion and the
    only item in the dropdown will be the native unit.
    """

    flux_unit_str = flux_unit.to_string()

    # if flux_unit is a spectral or photon flux density unit, then the flux unit
    # dropdown options should be the loaded unit (which may have a different
    # prefix e.g nJy) in addition to items in SPEC_PHOTON_FLUX_DENSITY_UNITS
    equiv = u.spectral_density(1 * u.m)  # spec. unit doesn't matter here, we're not evaluating
    for un in SPEC_PHOTON_FLUX_DENSITY_UNITS:
        if flux_unit.is_equivalent(un, equiv):
            if flux_unit_str not in SPEC_PHOTON_FLUX_DENSITY_UNITS:
                return SPEC_PHOTON_FLUX_DENSITY_UNITS + [flux_unit_str]
            else:
                return SPEC_PHOTON_FLUX_DENSITY_UNITS

    else:
        # for any other units, including counts, DN, e/s, DN /s, etc,
        # no other conversions between flux units available as we only support
        # conversions to and from spectral and photon flux density flux unit.
        # dropdown will only contain one item (the input unit)
        return [flux_unit_str]


def create_angle_equivalencies_list(solid_angle_unit):

    """
    Return valid angles that `solid_angle_unit` (which should be a solid angle
    physical type, or square pixel), can be translated to in the unit conversion
    plugin. These options will populate the dropdown menu for 'angle unit' in
    the  Unit Conversion plugin.

    Parameters
    ----------
    solid_angle_unit : str or u.Unit
        Unit object or string representation of unit that is a 'solid angle'
        or square pixel physical type.

    Returns
    -------
    equivalent_angle_units : list of str
        String representation of units that `solid_angle_unit` can be
        translated to.

    """

    if solid_angle_unit is None or solid_angle_unit is PIX2:
        # if there was no solid angle in the unit when calling this function
        # can only represent that unit as per square pixel
        return ['pix^2']

    # cast to unit then back to string to account for formatting inconsistencies
    # in strings that represent units
    if isinstance(solid_angle_unit, str):
        solid_angle_unit = u.Unit(solid_angle_unit)
    unit_str = solid_angle_unit.to_string()

    # uncomment and expand this list once translating between solid
    # angles and between solid angle and solid pixel is enabled
    # equivalent_angle_units = ['sr', 'pix^2']
    equivalent_angle_units = []
    if unit_str not in equivalent_angle_units:
        equivalent_angle_units += [unit_str]

    return equivalent_angle_units


def check_if_unit_is_per_solid_angle(unit, return_unit=False):
    """
    Check if a given Unit or unit string (that can be converted to
    a Unit) represents some unit per solid angle. If 'return_unit'
    is True, then a Unit of the solid angle will be returned (or
    None if no solid angle is present in the denominator).

    Parameters
    ----------
    unit : str or u.Unit
        u.Unit object or string representation of unit.
    return_unit : bool
        If True, the u.Unit of the solid angle unit will
        be returned (or None if unit is not a solid angle).

    Examples
    --------
    >>> check_if_unit_is_per_solid_angle('erg / (s cm^2 sr)')
    True
    >>> check_if_unit_is_per_solid_angle('erg / s cm^2')
    False
    >>> check_if_unit_is_per_solid_angle('Jy * sr^-1')
    True

    """

    # first, convert string to u.Unit obj.
    # this will take care of some formatting consistency like
    # turning something like Jy / (degree*degree) to Jy / deg**2
    # and erg sr^1 to erg / sr
    if isinstance(unit, (u.core.Unit, u.core.CompositeUnit,
                  u.core.IrreducibleUnit)):
        unit_str = unit.to_string()
    elif isinstance(unit, str):
        unit = u.Unit(unit)
        unit_str = unit.to_string()
    else:
        raise ValueError('Unit must be u.Unit, or string that can be converted into a u.Unit')

    if '/' in unit_str:
        # input unit might be comprised of several units in denom. so check all.
        denom = unit_str.split('/')[-1].split()

        # find all combos of one or two units, to catch cases where there are
        # two different units of angle in the denom that might comprise a solid
        # angle when multiplied.
        for i in [combo for length in (1, 2) for combo in itertools.combinations(denom, length)]:
            # turn tuple of 1 or 2 units into a string, and turn that into a u.Unit
            # to check type
            new_unit_str = ' '.join(i).translate(str.maketrans('', '', '()'))
            new_unit = u.Unit(new_unit_str)
            if new_unit.physical_type == 'solid angle':
                if return_unit:  # area units present and requested to be returned
                    return new_unit
                return True  # area units present but not requested to be returned
            # square pixel should be considered a square angle unit
            if new_unit == PIX2:
                if return_unit:
                    return new_unit
                return True

    # in the case there are no area units, but return units were requested
    if return_unit:
        return None

    # and if there are no area units, and return units were NOT requested.
    return False
