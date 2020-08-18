from asteval import Interpreter

import multiprocessing as mp
from multiprocessing import Pool

import numpy as np

import astropy.units as u

from specutils.spectra import Spectrum1D
from specutils.fitting import fit_lines

__all__ = ['fit_model_to_spectrum']


def fit_model_to_spectrum(spectrum, component_list, expression,
                          run_fitter=False):
    """
    Fits an astropy CompoundModel to a Spectrum1D instance.

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
        model and returns it without fitting - This is currently being
        ignored for 3D fits.

    Returns
    -------
    :class: `astropy.modeling.CompoundModel` or `list`
        The model resulting from the fit. In the case of a 1D input
        spectrum, a single model instance is returned. In case of a
        3D spectral cube input, instead o model instances for every
        spaxel, a list with 2D arrays, each one storing fitted parameter
        values for all spaxels, is returned.
    :class:`specutils.spectrum.Spectrum1D`
        The realization of the fitted model as a spectrum. The spectrum
        will be 1D or 3D depending on the input spectrum's shape.
    """
    # Initial guess for the fit.
    initial_model = _build_model(component_list, expression)

    if len(spectrum.shape) > 1:
        return _fit_3D(initial_model, spectrum)
    else:
        return _fit_1D(initial_model, spectrum, run_fitter)


def _fit_1D(initial_model, spectrum, run_fitter):
    """
    Fits an astropy CompoundModel to a Spectrum1D instance.

    Parameters
    ----------
    spectrum : :class:`specutils.spectrum.Spectrum1D`
        The spectrum to be fitted.
    initial_model : :class: `astropy.modeling.CompoundModel`
        Initial guess for the model to be fitted.
    run_fitter : bool
        When False (the default), the function composes the compound
        model and returns it without fitting.

    Returns
    -------
    :class: `astropy.modeling.CompoundModel`
        The model resulting from the fit.
    :class:`specutils.spectrum.Spectrum1D`
        The realization of the fitted model as a spectrum.

    """
    if run_fitter:
        output_model = fit_lines(spectrum, initial_model)
        output_values = output_model(spectrum.spectral_axis)
    else:
        # Return without fitting.
        output_model = initial_model
        output_values = initial_model(spectrum.spectral_axis)

    # Build return spectrum
    funit = spectrum.flux.unit
    output_spectrum = Spectrum1D(spectral_axis=spectrum.spectral_axis,
                                 flux=output_values * funit)

    return output_model, output_spectrum


def _fit_3D(initial_model, spectrum):
    """
    Fits an astropy CompoundModel to every spaxel in a cube
    using a multiprocessor pool running in parallel. Computes
    realizations of the models over each spaxel.

    Parameters
    ----------
    spectrum : :class:`specutils.spectrum.Spectrum1D`
        The spectrum that stores the cube in its 'flux' attribute.

    Returns
    -------
    :list: a list that stores 2D arrays. Each array contains one
        parameter from `astropy.modeling.CompoundModel` instances
        fitted to every spaxel in the input cube.
    :class:`specutils.spectrum.Spectrum1D`
        The spectrum that stores the fitted model values in its 'flux'
        attribute.
    """

    # Generate list of all spaxels to be fitted
    spaxels = _generate_spaxel_list(spectrum)

    # Build cube with empty slabs, one per model parameter. These
    # will store only parameter values for now, so a cube suffices.
    parameters_cube = np.zeros(shape=(len(initial_model.parameters),
                                      spectrum.flux.shape[0],
                                      spectrum.flux.shape[1]))

    # Build cube with empty arrays, one per input spaxel. These
    # will store the flux values corresponding to the fitted
    # model realization over each spaxel.
    output_flux_cube = np.zeros(shape=spectrum.flux.shape)

    # Callback to collect results from workers into the cubes
    def collect_result(results):
        for i in range(len(results['x'])):
            x = results['x'][i]
            y = results['y'][i]
            model = results['fitted_model'][i]
            fitted_values = results['fitted_values'][i]

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

    # The communicate overhead of spawning a process for each *individual*
    # parameter set is prohibitively high (it's actually faster to run things
    # sequentially). Instead, chunk the spaxel list based on the number of
    # available processors, and have each processor do the model fitting
    # on the entire subset of spaxel tuples, then return the set of results.
    for spx in np.array_split(spaxels, mp.cpu_count() - 1):
        # Worker for the multiprocess pool.
        worker = SpaxelWorker(spectrum.flux,
                              spectrum.spectral_axis,
                              initial_model,
                              param_set=spx)
        r = pool.apply_async(worker, callback=collect_result)
        results.append(r)
    for r in results:
        r.wait()

    pool.close()

    # Collect units from all parameters
    param_units = []
    for name in initial_model.param_names:
        param = getattr(initial_model, name)
        param_units.append(param.unit)

    # Re-format parameters cube to a list of 2D Quantity arrays.
    fitted_parameters = _handle_parameter_units(initial_model,
                                                parameters_cube,
                                                param_units)

    # Build output 3D spectrum
    funit = spectrum.flux.unit
    output_spectrum = Spectrum1D(spectral_axis=spectrum.spectral_axis,
                                 flux=output_flux_cube * funit)

    return fitted_parameters, output_spectrum


class SpaxelWorker:
    """
    A class with callable instances that perform fitting over a
    spaxel. It provides the callable for the `Pool.apply_async`
    function, and also holds everything necessary to perform the
    fit over one spaxel.

    Additionally, the callable computes the realization of the
    model just fitted, over that same spaxel. We cannot do these
    two steps (fit and compute) separately, since we cannot
    modify parameter values in an already built CompoundModel
    instance. We need to use the current model instance while
    it still exists.
    """
    def __init__(self, flux_cube, wave_array, initial_model, param_set):
        self.cube = flux_cube
        self.wave = wave_array
        self.model = initial_model
        self.param_set = param_set

    def __call__(self):
        results = {'x': [], 'y': [], 'fitted_model': [], 'fitted_values': []}

        for parameters in self.param_set:
            x = parameters[0]
            y = parameters[1]

            # Calling the Spectrum1D constructor for every spaxel
            # turned out to be less expensive than expected. Experiments
            # show that the cost amounts to a couple percent additional
            # running time in comparison with a version that uses a 3D
            # spectrum as input. Besides, letting an externally-created
            # spectrum reference into the callable somehow prevents it
            # to execute. This behavior was seen also with other functions
            # passed to the callable.
            flux = self.cube[x, y, :] # transposed!
            sp = Spectrum1D(spectral_axis=self.wave, flux=flux)

            fitted_model = fit_lines(sp, self.model)

            fitted_values = fitted_model(self.wave)

            results['x'].append(x)
            results['y'].append(y)
            results['fitted_model'].append(fitted_model)
            results['fitted_values'].append(fitted_values)

        return results


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
    # The expression parser needs the subcomponents stored in a
    # dict, with keys taken from their names. This mechanism can
    # be augmented with status feedback to the UI. This requires
    # the code in here to be refactored to provide the necessary
    # hooks for the GUI (see
    # specviz/specviz/plugins/model_editor/models.py around lines
    # 200-230).

    model_dict = {}

    for component in component_list:
        model_dict[component.name] = component

    aeval = Interpreter(usersyms=model_dict)
    model = aeval(expression)

    return model


def _handle_parameter_units(model, fitted_parameters_cube, param_units):
    """
    Extracts parameter units from a CompoundModel and parameter values
    from a list of 2D numpy arrays, and returns a list of 2D Quantity
    arrays built the parameter values and units respectively.

    Parameters
    ----------
    model : :class: `astropy.modeling.CompoundModel`
        An instance of a model.
    fitted_parameters_cube : `ndarray`
        A 3D array in which the 1st dimension addresses model
        parameters, and the 2nd and 3rd dimensions address
        spaxels.
    param_units : `list`
        A list with each parameter's units (this is not available
        in the model instance itself).

    Returns
    -------
    :list: list with 2D Quantity arrays
    """

    fitted_parameters_list = []

    for index in range(len(model.parameters)):
        _ary = fitted_parameters_cube[index, :, :]
        fitted_parameters_list.append(u.Quantity(_ary, param_units[index]))

    return fitted_parameters_list


def _generate_spaxel_list(spectrum):
    """
    Generates a list with tuples, each one addressing the (x,y)
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
