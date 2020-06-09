from asteval import Interpreter

import multiprocessing as mp
from multiprocessing import Pool

import numpy as np

import astropy.units as u

from specutils.spectra import Spectrum1D
from specutils.fitting import fit_lines

__all__ = ['fit_model_to_spectrum']


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

    initial_model = _build_model(component_list, expression)

    if len(spectrum.shape) > 1:
        # 3D case
        output_parameters, output_spectrum = _fit_model_to_cube(
            spectrum, component_list, expression)

        return output_parameters, output_spectrum
    else:
        # 1D case
        if run_fitter:
            output_model = fit_lines(spectrum, initial_model)
            output_values = output_model(spectrum.spectral_axis)
        else:
            # Return without fitting.
            output_model = initial_model
            output_values = initial_model(spectrum.spectral_axis)

        # Build return spectrum
        funit = spectrum.flux.unit
        output_spectrum = Spectrum1D(spectral_axis=spectrum.spectral_axis, flux=output_values * funit)

        return output_model, output_spectrum


def _fit_model_to_cube(spectrum, component_list, expression):
    """
    Fits an astropy CompoundModel to every spaxel in a cube
    using a multiprocessor pool running in parallel. Computes
    realizations of the models over each spaxel.

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
    :class:`specutils.spectrum.Spectrum1D`
        The spectrum that stores the fitted model values in its 'flux' attribute.
    """
    init_model = _build_model(component_list, expression)

    # Worker for the multiprocess pool.
    worker = SpaxelWorker(spectrum.flux,
                          spectrum.spectral_axis,
                          init_model)

    # Generate list of all spaxels to be fitted
    spaxels = _generate_spaxel_list(spectrum)

    # Build cube with empty slabs, one per model parameter. These
    # will store only parameter values for now, so a cube suffices.
    parameters_cube = np.zeros(shape=(len(init_model.parameters),
                                      spectrum.flux.shape[0],
                                      spectrum.flux.shape[1]))

    # Build cube with empty slabs, one per input spaxel. These
    # will store the flux values corresponding to the fitted
    # model realization over each spaxel.
    output_flux_cube = np.zeros(shape=spectrum.flux.shape)

    # Callback to collect results from workers into the cubes
    def collect_result(result):
        x = result[0]
        y = result[1]
        model = result[2]
        fitted_values = result[3]

        # Store fitted model parameters
        for index, name in enumerate(model.param_names):
            param = getattr(model, name)
            parameters_cube[index, x, y] = param.value

        # Store fitted values
        output_flux_cube[x, y, :] = fitted_values

    # Run multiprocessor pool to fit each spaxel and
    # compute model values on that same spaxel.
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

    # Re-format parameters cube to a list of 2D Quantity arrays.
    fitted_parameters = _extract_model_parameters(init_model, parameters_cube, param_units)

    # Build output 3D spectrum
    funit = spectrum.flux.unit
    output_spectrum = Spectrum1D(spectral_axis=spectrum.spectral_axis,
                                 flux=output_flux_cube * funit)

    return fitted_parameters, output_spectrum


class SpaxelWorker:
    '''
    A class with callable instances that perform fitting over a
    spaxel. It provides the callable for the `Pool.apply_async`
    function, and also holds everything necessary to perform the
    fit over one spaxel.

    Additionally, the callable computes the realization of the
    model just fitted, over that same spaxel. We cannot do these
    two steps (fit and compute) separately, since t=we cannot
    modify parameter values in an already built CompoundModel
    instance.
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
        fitted_values = fitted_model(self.wave)

        return (x, y, fitted_model, fitted_values)


def _build_model(component_list, expression):
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


def _generate_spaxel_list(spectrum):
    """
    Generates a list wuth tuples, each one addressing the (x,y)
    coordinates of a spaxel in a 3-D spectrum cube.

    Parameters
    ----------
    spectrum : :class:`specutils.spectrum.Spectrum1D`
        The spectrum that stores the cube in its 'flux' attribute.

    Returns
    -------
    :list: list with spaxels
    """
    spx = [[(x, y) for x in range(spectrum.flux.shape[0])]
           for y in range(spectrum.flux.shape[1])]

    spaxels = [item for sublist in spx for item in sublist]

    return spaxels


