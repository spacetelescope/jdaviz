from asteval import Interpreter

from specutils.spectra import Spectrum1D
from specutils.fitting import fit_lines

__all__ = ['fit_model_to_spectrum']


def fit_model_to_spectrum(spectrum, model, expression, window=()):
    """
    Fits an astropy CompoundModel to an instance of Spectrum1D.

    Parameters
    ----------
    spectrum : :class:`specutils.spectrum.Spectrum1D`
        The spectrum to be fitted.
    model : dict
        Spectral model subcomponents stored in a dict,
        with keys taken from their names.
    expression : str
        The arithmetic expression that combines together
        the model subcomponents.
    window : tuple
        The wavelength range where to fit.

    Returns
    -------
    :class:`astropy.modeling.CompoundModel`
        The realization of the fitted model.
    :class:`specutils.spectrum.Spectrum1D`
        The realization of the fitted model.
    """
    # Initial guess for the fit
    aeval = Interpreter(usersyms=model)
    compound_model_init = aeval(expression)

    # Do the fit
    fitted_model = fit_lines(spectrum, compound_model_init, window=window)
    fitted_values = fitted_model(spectrum.spectral_axis)

    # Build return spectrum
    funit = spectrum.flux.unit
    fitted_spectrum = Spectrum1D(spectral_axis=spectrum.spectral_axis, flux=fitted_values * funit)

    return fitted_model, fitted_spectrum