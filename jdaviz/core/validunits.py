import astropy.units as u
import numpy as np

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
    return [u.Unit(unit).name
            if u.Unit(unit) == u.Unit("Angstrom")
            else u.Unit(unit).long_names[0] if (
                hasattr(u.Unit(unit), "long_names") and len(u.Unit(unit).long_names) > 0)
            else u.Unit(unit).to_string()
            for unit in unit_list]


def create_spectral_equivalencies_list(spectrum,
                                       exclude=[u.jupiterRad, u.earthRad, u.solRad,
                                                u.lyr, u.AU, u.pc]):
    """Get all possible conversions from current spectral_axis_unit.
    """
    # Get unit equivalencies.
    curr_spectral_axis_unit_equivalencies = u.Unit(
        spectrum.spectral_axis.unit).find_equivalent_units(
        equivalencies=u.spectral())

    # Get local units.
    locally_defined_spectral_axis_units = ['angstrom', 'nanometer',
                                           'micron', 'hertz', 'erg']
    local_units = [u.Unit(unit) for unit in locally_defined_spectral_axis_units]

    # Remove overlap units.
    curr_spectral_axis_unit_equivalencies = list(set(curr_spectral_axis_unit_equivalencies)
                                                 - set(local_units+exclude))

    # Convert equivalencies into readable versions of the units and sorted alphabetically.
    spectral_axis_unit_equivalencies_titles = sorted(units_to_strings(
        curr_spectral_axis_unit_equivalencies))

    # Concatenate both lists with the local units coming first.
    spectral_axis_unit_equivalencies_titles = sorted(units_to_strings(
        local_units)) + spectral_axis_unit_equivalencies_titles

    return spectral_axis_unit_equivalencies_titles


def create_flux_equivalencies_list(spectrum):
    """Get all possible conversions for flux from current flux units.
    """
    # Get unit equivalencies.
    curr_flux_unit_equivalencies = u.Unit(
        spectrum.flux.unit).find_equivalent_units(
            equivalencies=u.spectral_density(np.sum(spectrum.spectral_axis)),
            include_prefix_units=False)

    # Get local units.
    locally_defined_flux_units = ['Jy', 'mJy', 'uJy',
                                  'W / (m2 Hz)',
                                  'eV / (s m2 Hz)',
                                  'erg / (s cm2)',
                                  'erg / (s cm2 um)',
                                  'erg / (s cm2 Angstrom)',
                                  'erg / (s cm2 Hz)',
                                  'ph / (s cm2 um)',
                                  'ph / (s cm2 Angstrom)',
                                  'ph / (s cm2 Hz)']
    local_units = [u.Unit(unit) for unit in locally_defined_flux_units]

    # Remove overlap units.
    curr_flux_unit_equivalencies = list(set(curr_flux_unit_equivalencies)
                                        - set(local_units))

    # Convert equivalencies into readable versions of the units and sort them alphabetically.
    flux_unit_equivalencies_titles = sorted(units_to_strings(curr_flux_unit_equivalencies))

    # Concatenate both lists with the local units coming first.
    flux_unit_equivalencies_titles = (sorted(units_to_strings(local_units)) +
                                      flux_unit_equivalencies_titles)

    return flux_unit_equivalencies_titles
