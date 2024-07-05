from astropy import units as u
import itertools

__all__ = ['units_to_strings', 'create_spectral_equivalencies_list',
           'create_flux_equivalencies_list', 'check_if_unit_is_per_solid_angle']


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
        return []

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


def create_flux_equivalencies_list(flux_unit, spectral_axis_unit):
    """Get all possible conversions for flux from current flux units."""
    if ((flux_unit in (u.count, u.dimensionless_unscaled))
            or (spectral_axis_unit in (u.pix, u.dimensionless_unscaled))):
        return []

    # Get unit equivalencies. Value passed into u.spectral_density() is irrelevant.
    try:
        curr_flux_unit_equivalencies = flux_unit.find_equivalent_units(
            equivalencies=u.spectral_density(1 * spectral_axis_unit),
            include_prefix_units=False)
    except u.core.UnitConversionError:
        return []

    # Get local flux units.
    locally_defined_flux_units = ['Jy', 'mJy', 'uJy', 'MJy',
                                  'W / (Hz m2)',
                                  'eV / (s m2 Hz)',
                                  'erg / (s cm2)',
                                  'erg / (s cm2 Hz)',
                                  'ph / (Angstrom s cm2)',
                                  'ph / (Hz s cm2)',
                                  'bol', 'AB', 'ST'
                                  ]
    local_units = [u.Unit(unit) for unit in locally_defined_flux_units]

    # Remove overlap units.
    curr_flux_unit_equivalencies = list(set(curr_flux_unit_equivalencies)
                                        - set(local_units))

    # Convert equivalencies into readable versions of the units and sort them alphabetically.
    flux_unit_equivalencies_titles = sorted(units_to_strings(curr_flux_unit_equivalencies))

    # Concatenate both lists with the local units coming first.
    return sorted(units_to_strings(local_units)) + flux_unit_equivalencies_titles

def create_sb_equivalencies_list(sb_unit, spectral_axis_unit):
    """Get all possible conversions for flux from current flux units."""
    if ((sb_unit in (u.count, u.dimensionless_unscaled))
            or (spectral_axis_unit in (u.pix, u.dimensionless_unscaled))):
        return []

    # Get unit equivalencies. Value passed into u.spectral_density() is irrelevant.
    try:
        curr_sb_unit_equivalencies = sb_unit.find_equivalent_units(
            equivalencies=u.spectral_density(1 * spectral_axis_unit),
            include_prefix_units=False)
    except u.core.UnitConversionError:
        return []

    locally_defined_sb_units = ['Jy / sr', 'mJy / sr', 'uJy / sr', 'MJy / sr', 'Jy / sr',
                                'W / (Hz sr m2)',
                                'eV / (Hz s sr m2)',
                                #'erg / (s cm2 sr)',
                                #'erg / (s cm2 Angstrom sr)',
                                #'erg / (s cm2 Hz sr)',
                                #'ph / (Angstrom s sr cm2)',
                                #'ph / (s cm2 Hz sr)',
                                'AB / sr']

    local_units = [u.Unit(unit) for unit in locally_defined_sb_units]

    exclude = []
    jansky_units = [u.Jy, u.mJy, u.uJy, u.MJy]

    for unit in jansky_units:
        if any(base in unit.bases for base in sb_unit.bases):
            exclude = [
                            u.ph / (u.Angstrom * u.s * u.sr * u.cm**2),
                            u.ph / (u.Hz * u.s * u.sr * u.cm**2),
                            u.ST / u.sr, u.bol / u.sr,
                            u.erg / (u.Angstrom * u.s * u.sr * u.cm**2),
                            u.erg / (u.Hz * u.s * u.sr * u.cm**2),
                            u.erg / (u.s * u.sr * u.cm**2)
                            ]

    # Remove overlap units.
    curr_sb_unit_equivalencies = list(set(curr_sb_unit_equivalencies)
                                      - set(local_units))

    # Convert equivalencies into readable versions of the units and sort them alphabetically.
    sb_unit_equivalencies_titles = sorted(units_to_strings(curr_sb_unit_equivalencies))

    # Concatenate both lists with the local units coming first.
    return sorted(units_to_strings(local_units)) + sb_unit_equivalencies_titles


def check_if_unit_is_per_solid_angle(unit):
    """
    Check if a given u.Unit or unit string (that can be converted to
    a u.Unit object) represents some unit per solid angle.

    Parameters
    ----------
    unit : str or u.Unit
        Unit object or string representation of unit.

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
    if isinstance(unit, u.core.Unit) or isinstance(unit, u.core.CompositeUnit):
        unit_str = unit.to_string()
    elif isinstance(unit, str):
        unit = u.Unit(unit)
        unit_str = unit.to_string()
    else:
        raise ValueError('Unit must be u.Unit, or string that can be converted into a u.Unit')

    if '/' in unit_str:
        # might be comprised of several units in denom.
        denom = unit_str.split('/')[-1].split()

        # find all combos of one or two units, to catch cases where there are two different
        # units of angle in the denom that might comprise a solid angle when multiplied.
        for i in [combo for length in (1, 2) for combo in itertools.combinations(denom, length)]:
            # turn tuple of 1 or 2 units into a string, and turn that into a u.Unit to check type
            new_unit_str = ' '.join(i).translate(str.maketrans('', '', '()'))
            new_unit = u.Unit(new_unit_str)
            if new_unit.physical_type == 'solid angle':
                return True

    return False
