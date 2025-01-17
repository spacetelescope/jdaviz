from collections.abc import Iterable
import itertools

from astropy import units as u
import numpy as np

from jdaviz.core.custom_units_and_equivs import (PIX2,
                                                 SPEC_PHOTON_FLUX_DENSITY_UNITS,
                                                 _eqv_pixar_sr,
                                                 _eqv_flux_to_sb_pixel,
                                                 _spectral_and_photon_flux_density_units)

__all__ = ["all_flux_unit_conversion_equivs", "check_if_unit_is_per_solid_angle",
           "combine_flux_and_angle_units", "convert_integrated_sb_unit",
           "create_equivalent_angle_units_list",
           "create_equivalent_flux_units_list",
           "create_equivalent_spectral_axis_units_list",
           "flux_conversion_general", "handle_squared_flux_unit_conversions",
           "supported_sq_angle_units", "spectral_axis_conversion",
           "units_to_strings"]


def all_flux_unit_conversion_equivs(pixar_sr=None, cube_wave=None):
    """
    Combines commonly used flux unit conversion equivalencies for
    translations between flux units and between flux and surface brightness
    units.

    - Flux to flux per square pixel
    - Flux to flux per steradian if ``pixar_sr`` is provided.
    - Spectral density conversions (e.g. Jy to erg/s/cm2/A), if ``cube_wave``
      is provided

    Parameters
    ----------
    pixar_sr : float, optional
        Pixel scale factor in steradians.
    cube_wave : `~astropy.units.Quantity`, optional
        A reference wavelength or frequency value(s).

    Returns
    -------
    equivs : list
        List of equivalencies.
    """

    equivs = _eqv_flux_to_sb_pixel()

    if pixar_sr is not None:
        equivs += _eqv_pixar_sr(pixar_sr)

    if cube_wave is not None:
        equivs += u.spectral_density(cube_wave)

    return equivs


def viewer_flux_conversion_equivalencies(values, spec):
    """
    Generate a list of flux and surface brightness unit conversion equivalencies
    specifically for converting units in the viewer, accounting for the special
    case of viewer limits that may need to index the spectral axis or list of
    pixel scale factors.

    This function assumes that if exactly two values are being converted, they
    represent the y-axis limits of the viewer. In this case, the first spectral
    axis value is used for spectral density conversions, and the min/max value
    of pixel scale factor are used if there are more than 2 values in
    meta['_pixel_scale_factor'].

    Parameters:
    ----------
    values : array-like
        The values to be converted, which may represent flux or surface brightness.
    spec : Spectrum1D

    Returns:
    -------
    equivs : list
        A list of unit equivalencies for flux and surface brightness conversions.
    """

    # if we are converting only 2 values, assume it is a viewer y limits case.
    is_viewer_limits = len(values) == 2

    # for viewer limits case, use only the 0th spectral axis value for spectral_density
    spectral_values = spec.spectral_axis
    if not np.isscalar(values) and is_viewer_limits:
        spectral_values = spectral_values[0]

    # Need this for setting the y-limits but values from viewer might be downscaled
    if len(values) != spectral_values.size:
        spectral_values = spec.spectral_axis[0]

    # Next, pixel scale factor
    pix_fac = None
    if '_pixel_scale_factor' in spec.meta:
        pix_fac = spec.meta['_pixel_scale_factor']

        if isinstance(pix_fac, u.Quantity):
            pix_fac = pix_fac.value

        # If 2 values are being converted (considered to be viewer y limits),
        # use min and max scale factors.
        if is_viewer_limits and isinstance(pix_fac, Iterable):
            pix_fac = [min(pix_fac), max(pix_fac)]

    # combine scale factor and spectral axis for u.spectral with other flux<>sb equivalencies
    equivs = all_flux_unit_conversion_equivs(pix_fac, spectral_values)

    return equivs


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

    Returns
    -------
    result : `~astropy.units.Unit`, bool, or `None`
        See explanation in ``return_unit``.

    Raises
    ------
    ValueError
        Invalid input.

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
        # convert string>unit>string to remove any formatting inconsistencies
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
            if new_unit.physical_type == 'solid angle' or new_unit == PIX2 or new_unit_str == 'spaxel':  # noqa
                # square pixel and spaxel should be considered square angle units
                if return_unit:  # area units present and requested to be returned
                    return new_unit
                return True  # area units present but not requested to be returned

    # in the case there are no area units, but return units were requested
    if return_unit:
        return None

    # and if there are no area units, and return units were NOT requested.
    return False


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

    return [(u.Unit(flux) / u.Unit(angle)).to_string() for flux in flux_units
            for angle in angle_units]


def create_equivalent_angle_units_list(solid_angle_unit):

    """
    Return valid angles that ``solid_angle_unit`` (which should be a solid angle
    physical type, or square pixel), can be translated to in the unit conversion
    plugin. These options will populate the dropdown menu for 'angle unit' in
    the  Unit Conversion plugin.

    Parameters
    ----------
    solid_angle_unit : str or u.Unit
        Unit object or string representation of unit that is a ``solid angle``
        or square pixel physical type.

    Returns
    -------
    equivalent_angle_units : list of str
        String representation of units that ``solid_angle_unit`` can be
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


def create_equivalent_flux_units_list(flux_unit):
    """
    Get all possible conversions for flux from flux_unit, to populate 'flux'
    dropdown menu in the unit conversion plugin.

    If flux_unit is a spectral or photon density (i.e., convertable to units in
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
    equiv = u.spectral_density(1 * u.m)  # unit doesn't matter, not evaluating
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


def create_equivalent_spectral_axis_units_list(spectral_axis_unit,
                                               exclude=[u.jupiterRad, u.earthRad,
                                                        u.solRad, u.lyr, u.AU,
                                                        u.pc, u.Bq, u.micron,
                                                        u.lsec]):
    """Get all possible conversions from current spectral_axis_unit."""
    if spectral_axis_unit in (u.pix, u.dimensionless_unscaled):
        return [spectral_axis_unit.to_string()]

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


def flux_conversion_general(values, original_unit, target_unit,
                            equivalencies=None, with_unit=True):
    """
    Converts ``values`` from ``original_unit`` to ``target_unit`` using the
    provided ``equivalencies`` while handling special cases where direct unit
    conversion is not possible. This function is designed to account for
    scenarios like conversions involving flux to surface brightness that
    also require a ``u.spectral_density`` equivalency, conversions between
    per-square pixel surface brightnesses that don't convert directly, and other
    flux to surface brightness conversions.

    This function should be used for unit conversions when possible instead of
    directly using Astropy's ``unit.to()``, as it handles additional logic for
    special cases.

    Parameters
    ----------
    values : array-like or float
        The numerical values to be converted.
    original_unit : `~astropy.units.Unit` or str
        The unit of the input values.
    target_unit : `~astropy.units.Unit` or str
        The desired unit to convert to.
    equivalencies : list of equivalencies, optional
        Unit equivalencies to apply during the conversion.
    with_unit : bool, optional
        If True, the returned value retains its unit. If False, only the
        numerical values are returned.

    Returns
    -------
    converted_values : `~astropy.units.Quantity` or float
        The converted values, with or without units based on ``with_unit``.

    Raises
    ------
    astropy.units.UnitConversionError
        If the conversion between ``original_unit`` and ``target_unit`` fails
        despite the provided equivalencies.

    """

    # we set surface brightness choices and selection before flux, which can
    # cause a dimensionless translation attempt at instantiation
    if not target_unit:
        return values

    if original_unit == target_unit:
        if not with_unit:
            return values
        return values * original_unit

    if isinstance(original_unit, str):
        original_unit = u.Unit(original_unit)
    if isinstance(target_unit, str):
        target_unit = u.Unit(target_unit)

    solid_angle_in_orig = check_if_unit_is_per_solid_angle(original_unit,
                                                           return_unit=True)
    solid_angle_in_targ = check_if_unit_is_per_solid_angle(target_unit,
                                                           return_unit=True)

    with u.set_enabled_equivalencies(equivalencies):

        # first possible case we want to catch before trying to translate: both
        # the original and target unit are per-pixel-squared SB units
        # and also require an additional equivalency, so we need to multiply out
        # the pix2 before conversion and re-apply. if this doesn't work, something else
        # is going on (missing equivalency, etc)
        if solid_angle_in_orig == solid_angle_in_targ == PIX2:
            converted_values = (values * (original_unit * PIX2)).to(target_unit * PIX2)
            converted_values = converted_values / PIX2  # re-apply pix2 unit
        else:
            try:
                # if units can be converted straight away with provided
                # equivalencies, return converted values
                converted_values = (values * original_unit).to(target_unit)
            except u.UnitConversionError:
                # the only other case where units with the correct equivs wouldn't
                # convert directly is if one unit is a flux and one is a sb and
                # they also require an additional equivalency
                if not bool(solid_angle_in_targ) == bool(solid_angle_in_orig):
                    converted_values = (values * original_unit * (solid_angle_in_orig or 1)).to(target_unit * (solid_angle_in_targ or 1))  # noqa
                    converted_values = (converted_values / (solid_angle_in_orig or 1)).to(target_unit)  # noqa
                else:
                    raise u.UnitConversionError(f'Could not convert {original_unit} to {target_unit} with provided equivalencies.')  # noqa

        if not with_unit:
            return converted_values.value

        return converted_values


def handle_squared_flux_unit_conversions(value, original_unit=None,
                                         target_unit=None, equivalencies=None):
    """
    Handles conversions between squared flux or surface brightness units
    that cannot be directly converted, even with the correct equivalencies.

    This function is specifically designed to address cases where squared
    units, such as (MJy/sr)**2 to (Jy/sr)**2, appear in contexts like
    variance columns of aperture photometry output tables. When additional
    equivalencies are required, direct conversion may fail, so this workaround.
    is required.

    Parameters
    ----------
    value : array or float
        The numerical values to be converted.
    original_unit : `astropy.units.Unit` or str
        The unit of the input values before conversion.
    target_unit : `astropy.units.Unit` or str
        The desired unit for the converted values.
    equivalencies : list of equivalencies
        Unit equivalencies to apply during the conversion.

    Returns
    -------
    converted : `~astropy.units.Quantity`
        The converted values, expressed in the ``target_unit``.
    """

    # get scale factor between non-squared units
    converted = flux_conversion_general(1.,
                                        original_unit ** 0.5,
                                        target_unit ** 0.5,
                                        equivalencies,
                                        with_unit=False)

    # square conversion factor and re-apply squared unit
    converted = converted ** 2 * value * target_unit

    return converted


def spectral_axis_conversion(values, original_units, target_units):
    eqv = u.spectral() + u.pixel_scale(1*u.pix)
    return (values * u.Unit(original_units)).to_value(u.Unit(target_units), equivalencies=eqv)


def supported_sq_angle_units(as_strings=False):
    """
    Returns a list of squared angle units supported by the app. If a new
    solid angle is added into unit conversion logic (e.g., square degree), it
    should be added here.
    """

    units = [PIX2, u.sr]
    if as_strings:
        units = units_to_strings(units)
    return units


def units_to_strings(unit_list):
    """Convert equivalencies into readable versions of the units.

    Parameters
    ----------
    unit_list : list
        List of either `astropy.units.Unit` or strings that can be converted
        to `astropy.units.Unit`.

    Returns
    -------
    result : list
        A list of the units with their best (i.e., most readable) string version.
    """
    return [u.Unit(unit).to_string() for unit in unit_list]


def convert_integrated_sb_unit(u1, spectral_axis_unit, desired_freq_unit, desired_length_unit):
    """
    Converts an integrated surface brightness unit (moment 0 unit) to a surface
    brighntess unit that is compatible with the spectral axis unit that the surface
    brightness was integrated over.

    This function adjusts an integrated flux unit to ensure compatibility with a given
    spectral axis unit (e.g., frequency or wavelength). The function handles conversions
    based on the physical type of the flux unit (per-frequency or per-wavelength) and
    the provided spectral axis unit.

    Parameters
    ----------
    u1 : astropy.units.Unit
        The unit of the integrated flux that needs conversion.

    spectral_axis_unit : astropy.units.Unit
        The unit of the spectral axis over which the flux was integrated (e.g., Angstrom
        for wavelength or Hz for frequency).

    Returns
    -------
    astropy.units.Unit
        The converted flux unit compatible with the given spectral axis unit. If the
        units are already compatible, the input unit ``u1`` is returned unchanged.
    """

    uu = u1 / spectral_axis_unit

    # multiply solid angle unit out of surface brightness to compare just flux components
    flux = uu * check_if_unit_is_per_solid_angle(uu.unit, return_unit=True)

    # then check if flux unit is a per-frequency or per-wavelength flux unit
    wav_units = _spectral_and_photon_flux_density_units(wav_only=True, as_units=True)
    freq_units = _spectral_and_photon_flux_density_units(freq_only=True, as_units=True)
    if np.any([flux.unit.is_equivalent(x) for x in wav_units]):
        flux_unit_type = 'length'
    elif np.any([flux.unit.is_equivalent(x) for x in freq_units]):
        flux_unit_type = 'frequency'

    if (spectral_axis_unit.physical_type != flux_unit_type):
        if flux_unit_type == 'length':
            spec_axis_conversion_scale_factor = (1*spectral_axis_unit).to(desired_length_unit,
                                                                          u.spectral())
        elif flux_unit_type == 'frequency':
            spec_axis_conversion_scale_factor = (1*spectral_axis_unit).to(desired_freq_unit,
                                                                          u.spectral())
    else:
        return u1  # units are compatible, return input

    return uu * spec_axis_conversion_scale_factor
