import numpy as np
import asdf
from astropy import units as u
from specutils import Spectrum

def _to_unit(x):
    """Coerce str/bytes/Unit to astropy.units.Unit."""
    if isinstance(x, bytes):
        x = x.decode()
    return u.Unit(x)

def is_roman_asdf(filename):
    """
    Check if the file is a Roman ASDF spectrum.
    This version is robust against None inputs and malformed files.
    """
    # Immediately return False if the filename is None to avoid errors.
    if filename is None:
        return False

    try:
        with asdf.open(filename) as af:
            # Use .get() with a default to prevent errors if 'roman' key is missing.
            roman = af.tree.get("roman", {})
            meta = roman.get("meta", {})
            data = roman.get("data", {})

            # Check for required keys and that 'data' is not empty in one step.
            if not all(k in meta for k in ["unit_wl", "unit_flux"]) or not data:
                return False

            # Safely get the first spectrum entry and check for its required keys.
            first_key = next(iter(data), None)
            spec = data.get(first_key, {})
            if not all(k in spec for k in ["wl", "flux"]):
                return False

            # If all checks pass, it's a valid file.
            return True

    except Exception:
        # If any error occurs during file opening or parsing, it's not a valid file.
        return False

def load_roman_asdf_spectrum(filename):
    """Load a Roman ASDF spectrum and convert it to Spectrum."""
    with asdf.open(filename) as af:
        roman = af["roman"]
        meta = roman["meta"]
        data = roman["data"]
        first_spectrum_key = list(data.keys())[0]
        spectrum = data[first_spectrum_key]
        wavelength = np.asarray(spectrum["wl"])
        flux = np.asarray(spectrum["flux"])
        wl_unit = _to_unit(meta["unit_wl"])
        flux_unit = _to_unit(meta["unit_flux"])

        # optional uncertainty (uncomment/adjust if your files provide these fields)
        # flux_error = spectrum.get("flux_error", None)
        # variance = spectrum.get("var", None)
        # uncertainty = None
        # if flux_error is not None:
        #     uncertainty = StdDevUncertainty(np.asarray(flux_error) * flux_unit)
        # elif variance is not None:
        #     var = np.asarray(variance) * (flux_unit ** 2)
        #     var = np.where(np.asarray(var.value) < 0, np.nan, var.value) * var.unit
        #     uncertainty = StdDevUncertainty(np.sqrt(var))
        
        spectrum1d = Spectrum(
            flux=flux * flux_unit,
            spectral_axis=wavelength * wl_unit
        )
        return spectrum1d