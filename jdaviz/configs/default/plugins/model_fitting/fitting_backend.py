from asteval import Interpreter

import multiprocessing as mp
from multiprocessing import Pool

import numpy as np

import astropy.units as u

from specutils.spectra import Spectrum1D
from specutils.fitting import fit_lines

__all__ = ['fit_model_to_spectrum']


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
    If the input spectrum represents a spectral cube, then fits
    an astropy CompoundModel to every spaxel in the cube, using
    a multiprocessor pool running in parallel.

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
    :class: `astropy.modeling.CompoundModel` or `list`
        The model resulting from the fit. In the case of a 1D input
        spectrum, a single model instance is returned. In case of a
        3D spectral cube input, a list with 2D arrays, each one storing
        fitted parameter values for all spaxels, is returned.
    :class:`specutils.spectrum.Spectrum1D`
        The realization of the fitted model as a spectrum. The spectrum will
        be 1D or 3D depending on the input spectrum.
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
    Fits an astropy CompoundModel to every spaxel in a cube
    using a multiprocessor pool running in parallel.

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
    :list: a list that stores 2D arrays. Each array contains one
        parameter from `astropy.modeling.CompoundModel` instances
        fitted to every spaxel in the input cube.
    """
    init_model = _build_initial_model(component_list, expression)

    # Worker for the multiprocess pool.
    worker = SpaxelWorker(spectrum.flux,
                          spectrum.spectral_axis,
                          init_model)

    # Generate list of all spaxels to be fitted
    spx = [[(x, y) for x in range(spectrum.flux.shape[0])]
           for y in range(spectrum.flux.shape[1])]
    spaxels = [item for sublist in spx for item in sublist]

    # Build cube with empty slabs, one per model parameter. These
    # will store only parameter values for now, so a cube suffices.
    result_cube = np.zeros(shape=(len(init_model.parameters),
                                  spectrum.flux.shape[0],
                                  spectrum.flux.shape[1]))

    # Callback to collect results from workers into the cube
    def collect_result(result):
        x = result[0]
        y = result[1]
        model = result[2]

        for index, name in enumerate(model.param_names):
            param = getattr(model, name)
            result_cube[index, x, y] = param.value

    # Run multiprocessor pool
    results = []
    pool = Pool(mp.cpu_count() - 1)

    for spx in spaxels:
        r = pool.apply_async(worker, (spx,), callback=collect_result)
        results.append(r)
    for r in results:
        r.wait()

    # Collect units from all parameters
    param_units = []
    for name in init_model.param_names:
        param = getattr(init_model, name)
        param_units.append(param.unit)

    # Re-format result to a list of 2D Quantity arrays.
    fitted_parameters = _extract_model_parameters(init_model, result_cube, param_units)

    return fitted_parameters


def _extract_model_parameters(model, fitted_parameters_cube, param_units):
    '''
    Extracts parameter units from a CompoundModel and parameter values
    from a list of 2D numpy arrays, and returns a list of 2D Quantity
    arrays built the parameter values and units respectively.

    :param model:
    :param fitted_parameters_cube:
    :param param_units:
    :return:
    '''
    fitted_parameters_list = []

    for index in range(len(model.parameters)):
        _ary = fitted_parameters_cube[index, :, :]
        fitted_parameters_list.append(u.Quantity(_ary, param_units[index]))

    return fitted_parameters_list


class SpaxelWorker:
    '''
    A class with callable instances. It provides the callable for
    the `Pool.apply_async` function, and also holds everything
    necessary to perform the fit over one spaxel.
    '''
    def __init__(self, flux_cube, wave_array, initial_model):
        self.cube = flux_cube
        self.wave = wave_array
        self.model = initial_model

    def __call__(self, parameters):
        x = parameters[0]
        y = parameters[1]

        flux = self.cube[x, y, :] # transposed!
        sp = Spectrum1D(spectral_axis=self.wave, flux=flux)
        fitted_model = fit_lines(sp, self.model)

        return (x, y, fitted_model)