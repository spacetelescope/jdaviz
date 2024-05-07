from astropy import units as u

__all__ = ['units_to_strings', 'create_spectral_equivalencies_list',
           'create_flux_equivalencies_list']


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

    # Get local units.
    if u.sr not in flux_unit.bases:
        locally_defined_flux_units = ['Jy', 'mJy', 'uJy', 'MJy', 'Jy',
                                      'W / (Hz m2)',
                                      'eV / (s m2 Hz)',
                                      'erg / (s cm2)',
                                      'erg / (s cm2 Angstrom)',
                                      'erg / (s cm2 Hz)',
                                      'ph / (s cm2 Angstrom)',
                                      'ph / (s cm2 Hz)']
        local_units = [u.Unit(unit) for unit in locally_defined_flux_units]
    else:
        locally_defined_flux_units = ['Jy / sr', 'mJy / sr', 'uJy / sr', 'MJy / sr', 'Jy / sr',
                                      'W / (Hz sr m2)',
                                      'eV / (s m2 Hz sr)',
                                      'erg / (s cm2 sr)',
                                      'erg / (s cm2 Angstrom sr)',
                                      'erg / (s cm2 Hz sr)',
                                      'ph / (s cm2 Angstrom sr)',
                                      'ph / (s cm2 Hz sr)',
                                      'bol / sr', 'AB / sr', 'ST / sr']
        local_units = [u.Unit(unit) for unit in locally_defined_flux_units]

    # Remove overlap units.
    curr_flux_unit_equivalencies = list(set(curr_flux_unit_equivalencies)
                                        - set(local_units))

    # Convert equivalencies into readable versions of the units and sort them alphabetically.
    flux_unit_equivalencies_titles = sorted(units_to_strings(curr_flux_unit_equivalencies))

    # Concatenate both lists with the local units coming first.
    return sorted(units_to_strings(local_units)) + flux_unit_equivalencies_titles
