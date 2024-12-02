import astropy.units as u

__all__ = ["PIX2", "SPEC_PHOTON_FLUX_DENSITY_UNITS",
           "_eqv_pixar_sr", "_eqv_flux_to_sb_pixel",
           "_eqv_sb_per_pixel_to_per_angle"]

# define custom composite units here
PIX2 = u.pix * u.pix


# Add spaxel to enabled units
def enable_spaxel_unit():
    spaxel = u.Unit('spaxel', represents=u.pixel, parse_strict='silent')
    u.add_enabled_units([spaxel])
    return


def _spectral_and_photon_flux_density_units(freq_only=False, wav_only=False,
                                            as_units=False):
    """
    Returns an alphabetically sorted list of string representations
    of flux density units supported by the unit conversion plugin. These units can
    be used for conversion if the input data units are compatible (i.e., directly
    equivalent or convertible using ``u.spectral_density(cube_wave)``). If both
    ``freq_only`` and ``wav_only`` are False, the function returns the combined
    list of all supported units. If ``as_units`` is True, return ``u.Unit`` instead
    of strings.

    Parameters:
    -----------
    freq_only : bool, optional
        If True, returns only frequency-based flux density units. (Default=False).

    wav_only : bool, optional
        If True, returns only wavelength-based flux density units. (Default=False).

    as_units : bool, optional
        If True, return ``u.Unit`` instead of strings

    Returns:
    --------
    list of str
        A sorted list of flux density unit strings.
    """
    wav_flux_units = ['erg / (Angstrom s cm2)', 'ph / (Angstrom s cm2)']
    freq_flux_units = ['Jy', 'mJy', 'uJy', 'MJy', 'W / (Hz m2)', 'eV / (Hz s m2)',
                       'erg / (Hz s cm2)', 'ph / (Hz s cm2)']

    if freq_only:
        flux_units = sorted(freq_flux_units)
    elif wav_only:
        flux_units = sorted(wav_flux_units)
    else:
        flux_units = sorted(freq_flux_units + wav_flux_units)

    if as_units:
        flux_units = [u.Unit(x) for x in flux_units]

    return flux_units


SPEC_PHOTON_FLUX_DENSITY_UNITS = _spectral_and_photon_flux_density_units()


def _eqv_pixar_sr(pixar_sr):
    """
    Return Equivalencies to convert from flux to flux per solid
    angle (aka surface brightness) using scale ratio ``pixar_sr``
    (steradians per pixel).
    """
    def converter_flux(x):  # Surface Brightness -> Flux
        return x * pixar_sr

    def iconverter_flux(x):  # Flux -> Surface Brightness
        return x / pixar_sr

    return [
        (u.MJy / u.sr, u.MJy, converter_flux, iconverter_flux),
        (u.erg / (u.s * u.cm**2 * u.Angstrom * u.sr), u.erg / (u.s * u.cm**2 * u.Angstrom), converter_flux, iconverter_flux),  # noqa
        (u.ph / (u.Angstrom * u.s * u.cm**2 * u.sr), u.ph / (u.Angstrom * u.s * u.cm**2), converter_flux, iconverter_flux),  # noqa
        (u.ph / (u.Hz * u.s * u.cm**2  * u.sr), u.ph / (u.Hz * u.s * u.cm**2), converter_flux, iconverter_flux),  # noqa
        (u.ct / u.sr, u.ct, converter_flux, iconverter_flux)  # noqa
    ]


def _eqv_flux_to_sb_pixel():
    """
    Returns an Equivalency between ``flux_unit`` and ``flux_unit`/pix**2``. This
    allows conversion between flux and flux-per-square-pixel surface brightness
    e.g MJy <> MJy / pix2
    """

    # generate an equivalency for each flux type that would need
    # another equivalency for converting to/from
    flux_units = [u.MJy,
                  u.erg / (u.s * u.cm**2 * u.Angstrom),
                  u.ph / (u.Angstrom * u.s * u.cm**2),
                  u.ph / (u.Hz * u.s * u.cm**2),
                  u.ct,
                  u.DN,
                  u.DN / u.s]

    equivs = [(flux_unit, flux_unit / PIX2, lambda x: x, lambda x: x)
              for flux_unit in flux_units]

    # We also need to convert between spaxel and pixel squared
    equivs += [(flux_unit / u.Unit('spaxel'), flux_unit / PIX2,
               lambda x: x, lambda x: x) for flux_unit in flux_units]

    return equivs


def _eqv_sb_per_pixel_to_per_angle(flux_unit, scale_factor=1):
    """
    Returns an equivalency between ``flux_unit`` per square pixel and
    ``flux_unit`` per solid angle to be able to compare and convert between units
    like Jy/pix**2 and Jy/sr. The scale factor is assumed to be in steradians,
    to follow the convention of the PIXAR_SR keyword.
    Note:
    To allow conversions between units like ``ph / (Hz s cm2 sr)`` and
    MJy / pix2, which would require this equivalency as well as u.spectral_density,
    these CAN'T be combined when converting like:
    equivalencies=u.spectral_density(1 * u.m) + _eqv_sb_per_pixel_to_per_angle(u.Jy)
    So additional logic is needed to compare units that need both equivalencies
    (one solution being creating this equivalency for each equivalent flux-type.)

    """

    # the two types of units we want to define a conversion between
    flux_solid_ang = flux_unit / u.sr
    flux_sq_pix = flux_unit / PIX2

    pix_to_solid_angle_equiv = [(flux_solid_ang, flux_sq_pix,
                                lambda x: x * scale_factor,
                                lambda x: x / scale_factor)]

    return pix_to_solid_angle_equiv
