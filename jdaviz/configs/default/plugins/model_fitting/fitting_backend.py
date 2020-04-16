from asteval import Interpreter

from specutils.spectra import Spectrum1D
from specutils.fitting import fit_lines

__all__ = ['fit_model_to_spectrum']


def fit_model_to_spectrum(spectrum, component_list, expression):
    """
    Fits an astropy CompoundModel to an instance of Spectrum1D.

    Parameters
    ----------
    spectrum : :class:`specutils.spectrum.Spectrum1D`
        The spectrum to be fitted.
    component_list : list
        Spectral model subcomponents stored in a list.
        Their `name` attribute must be unique.
    expression : str
        The arithmetic expression that combines together
        the model subcomponents. The subcomponents are
        refered via their 'name' attribute.

    Returns
    -------
    :class:`astropy.modeling.CompoundModel`
        The model resulting from the fit.
    :class:`specutils.spectrum.Spectrum1D`
        The realization of the fitted model as a spectrum.
    """
    # Initial guess for the fit.
    # The expression parser needs the subcomponents stored in a dict,
    # with keys taken from their names. This mechanism can be augmented
    # with status feedback to the UI. This requires the code in here to be
    # refactored to provide the necessary hooks for the GUI (see
    # specviz/specviz/plugins/model_editor/models.py around lines 200-230).

    model_dict = {}
    for component in component_list:
        model_dict[component.name] = component
    aeval = Interpreter(usersyms=model_dict)
    compound_model_init = aeval(expression)

    # Do the fit
    fitted_model = fit_lines(spectrum, compound_model_init)
    fitted_values = fitted_model(spectrum.spectral_axis)

    # Build return spectrum
    funit = spectrum.flux.unit
    fitted_spectrum = Spectrum1D(spectral_axis=spectrum.spectral_axis, flux=fitted_values * funit)

    return fitted_model, fitted_spectrum