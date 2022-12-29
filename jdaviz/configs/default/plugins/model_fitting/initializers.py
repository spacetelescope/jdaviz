"""
This module is used to initialize spectral models to the data at hand.

This is used by model-fitting code that has to create spectral model
instances with sensible parameter values such that they can be used as
first guesses by the fitting algorithms.
"""
import numpy as np

import astropy.modeling.models as models
from astropy import units as u

from jdaviz.models import BlackBody

__all__ = [
    'initialize',
    'get_model_parameters'
]

AMPLITUDE = 'amplitude'
POSITION = 'position'
WIDTH = 'width'

MODELS = {
     'Const1D': models.Const1D,
     'Linear1D': models.Linear1D,
     'Polynomial1D': models.Polynomial1D,
     'Gaussian1D': models.Gaussian1D,
     'Voigt1D': models.Voigt1D,
     'Lorentz1D': models.Lorentz1D,
     'PowerLaw1D': models.PowerLaw1D,
     'BlackBody': BlackBody
     }


def get_model_parameters(model_cls, model_kwargs={}):
    if isinstance(model_cls, str):
        model_cls = MODELS.get(model_cls)

    if model_cls.__name__ == 'Polynomial1D':
        # then the parameters are not stored, as they depend on the polynomial order
        degree = model_kwargs.get('degree', 1)
        return [f'c{n}' for n in range(degree + 1)]

    return model_cls.param_names


def _get_model_name(model):
    class_string = str(model.__class__)
    return class_string.split('\'>')[0].split(".")[-1]


class _Linear1DInitializer(object):
    """
    Initialization that is specific to the Linear1D model.

    Notes
    -----
    In a way, we need this specialized initializer because
    the linear 1D model is more like a kind of polynomial.
    It doesn't mesh well with other non-linear models.
    """
    def initialize(self, instance, x, y):
        """
        Initialize the model

        Parameters
        ----------
        instance : `~astropy.modeling.Model`
            The model to initialize.

        x, y : numpy.ndarray
            The data to use to initialize from.

        Returns
        -------
        instance : `~astropy.modeling.Model`
            The initialized model.
        """
        slope, intercept = np.polynomial.Polynomial.fit(x.value.flatten(), y.value.flatten(), 1)

        instance.slope.value = slope
        instance.intercept.value = intercept

        return instance


class _WideBand1DInitializer(object):
    """
    Initialization that is applicable to all "wide band"
    models

    A "wide band" model is one that has an amplitude and
    a position in wavelength space where this amplitude
    is defined.

    Parameters
    ----------
    factor: float
        The scale factor to apply to the amplitude
    """
    def __init__(self, factor=1.0):
        self._factor = factor

    def initialize(self, instance, x, y):
        """
        Initialize the model

        Parameters
        ----------
        instance: `~astropy.modeling.Model`
            The model to initialize.

        x, y: numpy.ndarray
            The data to use to initialize from.

        Returns
        -------
        instance: `~astropy.modeling.Model`
            The initialized model.
        """
        y_mean = np.mean(y)
        x_range = x[-1] - x[0]
        position = x_range / 2.0 + x[0]

        name = _get_model_name(instance)

        _setattr(instance, name, AMPLITUDE, y_mean * self._factor)
        _setattr(instance, name, POSITION, position)

        return instance


class _LineProfile1DInitializer(object):
    """
    Initialization that is applicable to all "line profile"
    models.

    A "line profile" model is one that has an amplitude, a width,
    and a defined position in wavelength space.

    Parameters
    ----------
    factor: float
        The scale factor to apply to the amplitude
    """
    def __init__(self, factor=1.0):
        self._factor = factor

    def _set_width_attribute(self, instance, name, fwhm):
        """
        Each line profile class has its own way of naming
        and defining the width parameter. Subclasses should
        override this method to conform to the specific
        definitions.

        Parameters
        ----------
        name : str
            The attribute name

        instance: `~astropy.modeling.Model`
            The model to initialize.

        fwhm : float
            FWHM
        """
        raise NotImplementedError

    def initialize(self, instance, x, y):
        """
        Initialize the model

        Parameters
        ----------
        instance: `~astropy.modeling.Model`
            The model to initialize.

        x, y: numpy.ndarray
            The data to use to initialize from.

        Returns
        -------
        instance: `~astropy.modeling.Model`
            The initialized model.
        """

        # X centroid estimates the position
        centroid = np.sum(x * y) / np.sum(y)

        # width can be estimated by the weighted
        # 2nd moment of the X coordinate.
        dx = x - np.mean(x)
        fwhm = 2 * np.sqrt(np.sum((dx * dx) * y) / np.sum(y))

        # amplitude is derived from area.
        delta_x = x[1:] - x[:-1]
        sum_y = np.sum((y[1:] - np.min(y[1:])) * delta_x)
        height = sum_y / (fwhm / 2.355 * np.sqrt(2 * np.pi))

        name = _get_model_name(instance)

        _setattr(instance, name, AMPLITUDE, height * self._factor)
        _setattr(instance, name, POSITION, centroid)

        self._set_width_attribute(instance, name, fwhm)

        return instance


class _Width_LineProfile1DInitializer(_LineProfile1DInitializer):
    def _set_width_attribute(self, instance, name, fwhm):
        _setattr(instance, name, WIDTH, fwhm)


class _Sigma_LineProfile1DInitializer(_LineProfile1DInitializer):
    def _set_width_attribute(self, instance, name, fwhm):
        _setattr(instance, name, WIDTH, fwhm / 2.355)


class _BlackBodyInitializer:
    """
    Initialization that is specific to the BlackBody model.

    Notes
    -----
    The fit is sensitive to the scale parameter as if it ever tries
    to go below zero, the fit will get stuck at 0 (without imposed
    parameter limits)
    """
    def initialize(self, instance, x, y):
        """
        Initialize the model

        Parameters
        ----------
        instance: `~astropy.modeling.Model`
            The model to initialize.

        x, y: numpy.ndarray
            The data to use to initialize from.

        Returns
        -------
        instance: `~astropy.modeling.Model`
            The initialized model.
        """
        y_mean = np.nanmean(y)

        # The y-unit could contain a scale factor (like 1e-7 * FLAM).  We
        # need to account for this in our dimensionless scale factor guess.
        # We could make this smarter if we also made a guess for the temperature
        # based on the peak wavelength/frequency and then estimated the amplitude,
        # but just getting within an order of magnitude should help significantly
        y_unit_scaled = y.unit
        for native_output_unit in instance._native_output_units.values():
            if y_unit_scaled.is_equivalent(native_output_unit):
                y_mean = y_mean.to(native_output_unit)
                break

        instance.scale = y_mean.value * u.dimensionless_unscaled

        return instance


def _setattr(instance, mname, pname, value):
    """
    Sets parameter value by mapping parameter name to model type.

    Prevents the parameter value setting to be stopped on its tracks
    by non-existent model names or parameter names.

    Parameters
    ----------
    instance: `~astropy.modeling.Model`
        The model to initialize.

    mname: str
        Model name.

    pname: str
        Parameter name.

    value: any
        The value to assign.
    """
    try:
        setattr(instance, _p_names[mname][pname], value)
    except KeyError:
        pass


# This associates each initializer to its corresponding spectral model.
# Some models are not really line profiles, but their parameter names
# and roles are the same as in a typical line profile, so they can be
# initialized in the same way.
_initializers = {
    'Beta1D':                      _WideBand1DInitializer,  # noqa
    'Const1D':                     _WideBand1DInitializer,  # noqa
    'PowerLaw1D':                  _WideBand1DInitializer,  # noqa
    'BrokenPowerLaw1D':            _WideBand1DInitializer,  # noqa
    'ExponentialCutoffPowerLaw1D': _WideBand1DInitializer,  # noqa
    'LogParabola1D':               _WideBand1DInitializer,  # noqa
    'Box1D':                       _Width_LineProfile1DInitializer,  # noqa
    'Gaussian1D':                  _Sigma_LineProfile1DInitializer,  # noqa
    'Lorentz1D':                   _Width_LineProfile1DInitializer,  # noqa
    'Voigt1D':                     _Width_LineProfile1DInitializer,  # noqa
    'MexicanHat1D':                _Sigma_LineProfile1DInitializer,  # noqa
    'Trapezoid1D':                 _Width_LineProfile1DInitializer,  # noqa
    'Linear1D':                    _Linear1DInitializer,  # noqa
    'BlackBody':                   _BlackBodyInitializer,  # noqa
    # 'Spline1D':                   spline.Spline1DInitializer
}

# Models can have parameter names that are similar amongst them, but not quite the same.
# This maps the standard names used in the code to the actual names used by astropy.
_p_names = {
    'Gaussian1D':                  {AMPLITUDE: 'amplitude',  POSITION: 'mean', WIDTH: 'stddev'},  # noqa
    'GaussianAbsorption':          {AMPLITUDE: 'amplitude',  POSITION: 'mean', WIDTH: 'stddev'},  # noqa
    'Lorentz1D':                   {AMPLITUDE: 'amplitude',  POSITION: 'x_0',  WIDTH: 'fwhm'},  # noqa
    'Voigt1D':                     {AMPLITUDE: 'amplitude_L', POSITION: 'x_0',  WIDTH: 'fwhm_G'},  # noqa
    'Box1D':                       {AMPLITUDE: 'amplitude',  POSITION: 'x_0',  WIDTH: 'width'},  # noqa
    'MexicanHat1D':                {AMPLITUDE: 'amplitude',  POSITION: 'x_0',  WIDTH: 'sigma'},  # noqa
    'Trapezoid1D':                 {AMPLITUDE: 'amplitude',  POSITION: 'x_0',  WIDTH: 'width'},  # noqa
    'Beta1D':                      {AMPLITUDE: 'amplitude',  POSITION: 'x_0'},  # noqa
    'PowerLaw1D':                  {AMPLITUDE: 'amplitude',  POSITION: 'x_0'},  # noqa
    'ExponentialCutoffPowerLaw1D': {AMPLITUDE: 'amplitude',  POSITION: 'x_0'},  # noqa
    'LogParabola1D':               {AMPLITUDE: 'amplitude',  POSITION: 'x_0'},  # noqa
    'BrokenPowerLaw1D':            {AMPLITUDE: 'amplitude',  POSITION: 'x_break'},  # noqa
    'Const1D':                     {AMPLITUDE: 'amplitude'},  # noqa
    }


def initialize(instance, x, y):
    """
    Initialize given model.

    X and Y are for now Quantity arrays with the
    independent and dependent variables. It's assumed X values
    are stored in increasing order in the array.

    Parameters
    ----------
    instance : `~astropy.modeling.Model`
        The model to initialize.

    x, y : ndarray
        The data to use to initialize from.

    Returns
    -------
    instance : `~astropy.modeling.Model`
        The initialized model.
        If there are any errors, the instance is returned
        uninitialized.
    """
    if x is None or y is None:
        return instance

    name = _get_model_name(instance)

    try:
        initializer = _initializers[name]()

        return initializer.initialize(instance, x, y)

    except KeyError:
        return instance
