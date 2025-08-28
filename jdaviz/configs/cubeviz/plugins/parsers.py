import warnings

import numpy as np
from astropy import units as u
from specutils import Spectrum

from jdaviz.core.custom_units_and_equivs import PIX2, _eqv_flux_to_sb_pixel
from jdaviz.core.unit_conversion_utils import check_if_unit_is_per_solid_angle

__all__ = []


def _return_spectrum_with_correct_units(flux, wcs, metadata, data_type=None,
                                        target_wave_unit=None, hdulist=None,
                                        uncertainty=None, mask=None, apply_pix2=False,
                                        spectral_axis=None):
    """Upstream issue of WCS not using the correct units for data must be fixed here.
    Issue: https://github.com/astropy/astropy/issues/3658.

    Also converts flux units to flux/pix2 solid angle units, if `flux` is not a surface
    brightness and `apply_pix2` is True.
    """
    # handle scale factors when they are included in the unit
    # (has to be done before Spectrum creation)
    if not np.isclose(flux.unit.scale, 1, rtol=1e-5):
        flux = flux.to(flux.unit / flux.unit.scale)

    with warnings.catch_warnings():
        warnings.filterwarnings(
            'ignore', message='Input WCS indicates that the spectral axis is not last',
            category=UserWarning)
        if spectral_axis is None:
            sc = Spectrum(flux=flux, wcs=wcs, uncertainty=uncertainty, mask=mask, meta=metadata)
        else:
            sc = Spectrum(flux=flux, spectral_axis=spectral_axis,
                          uncertainty=uncertainty, mask=mask, meta=metadata)

    # convert flux and uncertainty to per-pix2 if input is not a surface brightness
    target_flux_unit = None
    if (apply_pix2 and (data_type != "mask") and
            (not check_if_unit_is_per_solid_angle(flux.unit))):
        target_flux_unit = flux.unit / PIX2
    elif check_if_unit_is_per_solid_angle(flux.unit, return_unit=True) == "spaxel":
        # We need to convert spaxel to pixel squared, since spaxel isn't fully supported by astropy
        # This is horribly ugly but just multiplying by u.Unit("spaxel") doesn't work
        target_flux_unit = flux.unit * u.Unit('spaxel') / PIX2

    if target_wave_unit is None and hdulist is not None:
        found_target = False
        for ext in ('SCI', 'FLUX', 'PRIMARY', 'DATA'):  # In priority order
            if found_target:
                break
            if ext not in hdulist:
                continue
            hdr = hdulist[ext].header
            # The WCS could be swapped or unswapped.
            for cunit_num in (3, 1):
                cunit_key = f"CUNIT{cunit_num}"
                ctype_key = f"CTYPE{cunit_num}"
                if cunit_key in hdr and 'WAV' in hdr[ctype_key]:
                    target_wave_unit = u.Unit(hdr[cunit_key])
                    found_target = True
                    break

    if target_wave_unit == sc.spectral_axis.unit:
        target_wave_unit = None

    if (target_wave_unit is None) and (target_flux_unit is None):  # Nothing to convert
        new_sc = sc
    elif target_flux_unit is None:  # Convert wavelength only
        new_sc = sc.with_spectral_axis_unit(target_wave_unit)
    elif target_wave_unit is None:  # Convert flux only and only PIX2 stuff
        new_sc = sc.with_flux_unit(target_flux_unit, equivalencies=_eqv_flux_to_sb_pixel())
    else:  # Convert both
        new_sc = sc.with_spectral_axis_and_flux_units(
            target_wave_unit, target_flux_unit, flux_equivalencies=_eqv_flux_to_sb_pixel())

    if target_wave_unit is not None:
        new_sc.meta['_orig_spec'] = sc  # Need this for later

    return new_sc
