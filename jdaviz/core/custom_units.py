import astropy.units as u

__all__ = ["PIX2", "SPEC_PHOTON_FLUX_DENSITY_UNITS"]

# define custom composite units here
PIX2 = u.pix * u.pix


def _spectral_and_photon_flux_density_units():
    """
    This function returns an alphabetically sorted list of string representations
    of spectral and photon flux density units. This list represents flux units
    that the unit conversion plugin supports conversion to and from if the input
    data unit is compatible with items in the list (i.e is equivalent directly
    or with u.spectral_density(cube_wave)).
    """
    flux_units = ['Jy', 'mJy', 'uJy', 'MJy', 'W / (Hz m2)', 'eV / (Hz s m2)',
                  'erg / (Hz s cm2)', 'erg / (Angstrom s cm2)',
                  'ph / (Angstrom s cm2)', 'ph / (Hz s cm2)']

    return sorted(flux_units)


SPEC_PHOTON_FLUX_DENSITY_UNITS = _spectral_and_photon_flux_density_units()
