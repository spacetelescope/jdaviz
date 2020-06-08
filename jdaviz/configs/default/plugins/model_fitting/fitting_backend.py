from asteval import Interpreter

from specutils.spectra import Spectrum1D
from specutils.fitting import fit_lines

__all__ = ['fit_model_to_spectrum', 'fit_model_to_cube']


def _build_initial_model(component_list, expression):
    """
    Builds an astropy CompoundModel from a list of components
    and an expression that links them to each other.

    Parameters
    ----------
    component_list : list
        Spectral model subcomponents stored in a list.
        Their `name` attribute must be unique. Each subcomponent
        should be an initialized object from `astropy.modeling.models'
    expression : str
        The arithmetic expression that combines together
        the model subcomponents. The subcomponents are
        refered via their 'name' attribute.

    Returns
    -------
    :class:`astropy.modeling.CompoundModel`
        The model resulting from the fit.
    """
    model_dict = {}

    for component in component_list:
        model_dict[component.name] = component

    aeval = Interpreter(usersyms=model_dict)
    compound_model_init = aeval(expression)

    return compound_model_init


def fit_model_to_spectrum(spectrum, component_list, expression, run_fitter=False):
    """
    Fits an astropy CompoundModel to an instance of Spectrum1D.

    Parameters
    ----------
    spectrum : :class:`specutils.spectrum.Spectrum1D`
        The spectrum to be fitted.
    component_list : list
        Spectral model subcomponents stored in a list.
        Their `name` attribute must be unique. Each subcomponent
        should be an initialized object from `astropy.modeling.models'
    expression : str
        The arithmetic expression that combines together
        the model subcomponents. The subcomponents are
        refered via their 'name' attribute.
    run_fitter : bool
        When False (the default), the function composes the compound
        model and returns it without fitting.

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

    compound_model_init = _build_initial_model(component_list, expression)

    if run_fitter:
        output_model = fit_lines(spectrum, compound_model_init)
        output_values = output_model(spectrum.spectral_axis)
    else:
        # Return without fitting.
        output_model = compound_model_init
        output_values = compound_model_init(spectrum.spectral_axis)

    # Build return spectrum
    funit = spectrum.flux.unit
    output_spectrum = Spectrum1D(spectral_axis=spectrum.spectral_axis, flux=output_values * funit)

    return output_model, output_spectrum


def fit_model_to_cube(spectrum, component_list, expression):
    """
    Fits an astropy CompoundModel to every spaxel in a cube.

    Parameters
    ----------
    spectrum : :class:`specutils.spectrum.Spectrum1D`
        The spectrum that stores the cube in its 'flux' attribute.
    component_list : list
        Spectral model subcomponents stored in a list.
        Their `name` attribute must be unique. Each subcomponent
        should be an initialized object from `astropy.modeling.models'
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
    compound_model_init = _build_initial_model(component_list, expression)

    output_model = fit_lines(spectrum, compound_model_init)
    output_values = output_model(spectrum.spectral_axis)

    # Build return spectrum
    funit = spectrum.flux.unit
    output_spectrum = Spectrum1D(spectral_axis=spectrum.spectral_axis, flux=output_values * funit)

    return output_model, output_spectrum


