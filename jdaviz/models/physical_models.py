# Licensed under a 3-clause BSD style license - see LICENSE.rst
# copied and modified from astropy: https://github.com/astropy/astropy/pull/12304
"""
Models that have physical origins.
"""
# pylint: disable=invalid-name, no-member

import warnings

import numpy as np

from astropy import constants as const
from astropy import units as u
from astropy.utils.exceptions import AstropyUserWarning
from astropy.modeling.core import Fittable1DModel
from astropy.modeling.parameters import Parameter

__all__ = ["BlackBody"]

# ASTROPY_LT_5_3
__doctest_requires__ = {"BlackBody": ["astropy<5.3"]}


class BlackBody(Fittable1DModel):
    """
    Blackbody model using the Planck function.

    Parameters
    ----------
    temperature : `~astropy.units.Quantity` ['temperature']
        Blackbody temperature.

    scale : float or `~astropy.units.Quantity` ['dimensionless']
        Scale factor

    output_units: `~astropy.units.CompositeUnit` or string
        Desired output units when evaluating.  If a unit object,
        must be equivalent to one of erg / (cm ** 2 * s * Hz * sr)
        or erg / (cm ** 2 * s * AA * sr) for surface brightness
        or erg / (cm ** 2 * s * Hz) or erg / (cm ** 2 * s * AA) for
        flux density (in which case the pi is included internally
        and should not be passed in `scale` - see notes below).
        If a string, can be one of 'SNU', 'SLAM', 'FNU', 'FLAM'
        which reference the units above, respectively.

    Notes
    -----

    Model formula:

        .. math:: B_{\\nu}(T) = A \\frac{2 h \\nu^{3} / c^{2}}{exp(h \\nu / k T) - 1}

    Deprecated support for non-dimensionless units in `scale`:

        If `scale` is passed with non-dimensionless units that are equivalent
        to one of the supported `output_units`, the unit is stripped and interpreted
        as `output_units` and the float value will account for the scale between
        the passed units and native `output_units`.  If `scale` includes flux units,
        the value will be divided by pi (since solid angle is included in the units),
        and re-added internally when returning results.  Note that this can result in
        ambiguous and unexpected results.  To avoid confusion, pass unitless
        `scale` and `output_units` separately.

    Examples
    --------
    >>> from astropy.modeling import models
    >>> from astropy import units as u
    >>> bb = models.BlackBody(temperature=5000*u.K)
    >>> bb(6000 * u.AA)  # doctest: +FLOAT_CMP
    <Quantity 1.53254685e-05 erg / (cm2 Hz s sr)>

    .. plot::
        :include-source:

        import numpy as np
        import matplotlib.pyplot as plt

        from astropy.modeling.models import BlackBody
        from astropy import units as u
        from astropy.visualization import quantity_support

        bb = BlackBody(temperature=5778*u.K)
        wav = np.arange(1000, 110000) * u.AA
        flux = bb(wav)

        with quantity_support():
            plt.figure()
            plt.semilogx(wav, flux)
            plt.axvline(bb.nu_max.to(u.AA, equivalencies=u.spectral()).value, ls='--')
            plt.show()
    """

    # We parametrize this model with a temperature and a scale.
    temperature = Parameter(default=5000.0, min=0, unit=u.K, description="Blackbody temperature")
    scale = Parameter(default=1.0, min=0, description="Scale factor")

    # We allow values without units to be passed when evaluating the model, and
    # in this case the input x values are assumed to be frequencies in Hz or wavelengths
    # in AA (depending on the choice of output_units).
    _input_units_allow_dimensionless = True

    # We enable the spectral equivalency by default for the spectral axis
    input_units_equivalencies = {'x': u.spectral()}

    # Store the native units returned by B_nu equation
    _native_units = u.erg / (u.cm ** 2 * u.s * u.Hz * u.sr)

    # Store the base native output units.  If scale is passed with units
    # equivalent to these, the dimensionless factor is converted to these
    # units.
    _native_output_units = {'FNU': u.erg / (u.cm ** 2 * u.s * u.Hz),
                            'FLAM': u.erg / (u.cm ** 2 * u.s * u.AA),
                            'SNU': u.erg / (u.cm ** 2 * u.s * u.Hz * u.sr),
                            'SLAM': u.erg / (u.cm ** 2 * u.s * u.AA * u.sr)}

    # Until unit-support on scale is removed, let's raise a warning for the ambiguous cases
    # when calling bolometric_flux
    _bolometric_flux_ambig_warn = False

    def __init__(self, *args, **kwargs):
        output_units = kwargs.pop('output_units', None)
        scale = kwargs.get('scale', None)

        # DEPRECATE: for now we'll continue to support scale with non-dimensionless units
        # by stripping the unit and applying that to output_units.
        if hasattr(scale, 'unit') and not scale.unit.is_equivalent(u.dimensionless_unscaled):
            if output_units is None:
                # NOTE: output_units will have to pass validation when assigned below
                # so we don't need to duplicate the checks here
                output_units = scale.unit

                # NOTE: if the scale units are equivalent (but not identical) to the
                # "native" output units, we want to convert the dimensionless scale
                # to account for the scaling between these units.  This is self-consistent
                # with the treatment of pi below for flux units, and addresses
                # https://github.com/astropy/astropy/issues/11547#issuecomment-823772098
                # but is a change in behavior from the previous treatment where the
                # float value was treated as the scale factor, ignoring units
                for native_output_unit in self._native_output_units.values():
                    if output_units.is_equivalent(native_output_unit):
                        scale = scale.to(native_output_unit)
                        break

                # If the scale had FNU or FLAM units, then the scale quantity INCLUDES
                # pi*u.sr.  We need to remove the pi when passing the dimensionless
                # scale as it will be re-added later in evaluate.
                if output_units.is_equivalent(self._native_units*u.sr, u.spectral_density(1*u.Hz)):
                    kwargs['scale'] = scale.value / np.pi
                else:
                    kwargs['scale'] = scale.value

                self._bolometric_flux_ambig_warn = True

            else:
                # Do not allow passing scale with unit AND output_units
                # (even though they may be the same)
                raise ValueError("cannot pass output_units and scale with units")

        self.output_units = output_units
        return super().__init__(*args, **kwargs)

    def evaluate(self, x, temperature, scale):
        """Evaluate the model.

        Parameters
        ----------
        x : float, `~numpy.ndarray`, or `~astropy.units.Quantity` ['frequency']
            Frequency at which to compute the blackbody. If no units are given,
            this defaults to Hz.

        temperature : float, `~numpy.ndarray`, or `~astropy.units.Quantity`
            Temperature of the blackbody. If no units are given, this defaults
            to Kelvin.

        scale : float, `~numpy.ndarray`, or `~astropy.units.Quantity` ['dimensionless']
            Desired scale for the blackbody.

        Returns
        -------
        y : number or ndarray
            Blackbody spectrum. The units are determined from the units of
            ``scale``.

        .. note::

            Use `numpy.errstate` to suppress Numpy warnings, if desired.

        .. warning::

            Output values might contain ``nan`` and ``inf``.

        Raises
        ------
        ValueError
            Invalid temperature.

        ZeroDivisionError
            Wavelength is zero (when converting to frequency).
        """
        if not isinstance(temperature, u.Quantity):
            in_temp = u.Quantity(temperature, u.K)
        else:
            in_temp = temperature

        if not isinstance(x, u.Quantity):
            # then we assume it has input_units which depends on the
            # requested output units (either Hz or AA)
            in_x = u.Quantity(x, self.input_units['x'])
        else:
            in_x = x

        # Convert to units for calculations, also force double precision
        with u.add_enabled_equivalencies(u.spectral() + u.temperature()):
            freq = u.Quantity(in_x, u.Hz, dtype=np.float64)
            temp = u.Quantity(in_temp, u.K)

        # Check if input values are physically possible
        if np.any(temp < 0):
            raise ValueError(f"Temperature should be positive: {temp}")
        if not np.all(np.isfinite(freq)) or np.any(freq <= 0):
            warnings.warn(
                "Input contains invalid wavelength/frequency value(s)",
                AstropyUserWarning,
            )

        log_boltz = const.h * freq / (const.k_B * temp)
        boltzm1 = np.expm1(log_boltz)

        # Calculate blackbody flux
        bb_nu = 2.0 * const.h * freq ** 3 / (const.c ** 2 * boltzm1) / u.sr

        if self.scale.unit is not None:
            # Will be dimensionless at this point, but may not be dimensionless_unscaled
            if not hasattr(scale, 'unit'):
                # during fitting, scale will be passed without units
                # but we still need to convert from the input dimensionless
                # to dimensionless unscaled
                scale = scale * self.scale.unit
            scale = scale.to(u.dimensionless_unscaled)

        if self.output_units.is_equivalent(self._native_units, u.spectral_density(freq)):
            # then requesting SNU or SLAM
            bb_unit = self.output_units
            scale = scale  # dimensionless
        else:
            # then requesting FNU or FLAM, which means the bb_unit
            # needs to be the requested output units without sr
            # and we'll then multiply by pi * u.sr separately
            bb_unit = self.output_units / u.sr
            scale = scale * np.pi * u.sr

        y = scale * bb_nu.to(bb_unit, u.spectral_density(freq))

        # If the temperature parameter has no unit, we should return a unitless
        # value. This occurs for instance during fitting, since we drop the
        # units temporarily.
        if hasattr(temperature, "unit"):
            return y
        return y.value

    @property
    def output_units(self):
        if self._output_units is None:
            # default to SNU if not passed (or set internally from units on scale)
            return u.erg / (u.cm ** 2 * u.s * u.Hz * u.sr)
        return self._output_units

    @output_units.setter
    def output_units(self, unit):
        """ Ensure `output_units` is valid."""
        if isinstance(unit, str):
            if unit in ['SNU', 'SLAM', 'FNU', 'FLAM']:
                # let's provide some convenience for passing these as strings
                unit = self._native_output_units.get(unit)
            else:
                try:
                    unit = u.Unit(unit)
                except ValueError:
                    # then the string wasn't a valid unit, we'll allow the error below to be raised
                    pass

        if unit is None:
            pass
        elif isinstance(unit, u.UnitBase):
            # support SNU, SLAM, FNU, FLAM output units (and equivalent)
            if not (unit.is_equivalent(self._native_units, u.spectral_density(1*u.AA)) or
                    unit.is_equivalent(self._native_units*u.sr, u.spectral_density(1*u.AA))):
                raise ValueError(f"output_units not in surface brightness or flux density: {unit}")
        else:
            raise ValueError("output_units must be of type Unit, None, "
                             "or one of 'SNU', 'SLAM', 'FNU', 'FLAM'")

        self._output_units = unit

    @property
    def input_units(self):
        # The input units are those of the 'x' value, which will depend on the
        # units compatible with the expected output units.
        output_units = self.output_units
        if (output_units.is_equivalent(self._native_output_units['SNU']) or
                output_units.is_equivalent(self._native_output_units['FNU'])):
            return {self.inputs[0]: u.Hz}
        else:
            return {self.inputs[0]: u.AA}

    def _parameter_units_for_data_units(self, inputs_unit, outputs_unit):
        return {"temperature": u.K}

    @property
    def bolometric_flux(self):
        """Bolometric flux."""
        if self.scale.unit is not None:
            # Will be dimensionless at this point, but may not be dimensionless_unscaled
            scale = self.scale.quantity.to(u.dimensionless_unscaled)
        else:
            scale = self.scale.value

        if self._bolometric_flux_ambig_warn:
            warnings.warn(
                f"scale was originally passed with units, "
                f"but being treated as unitless with value={scale}",
                AstropyUserWarning,
            )

        # bolometric flux in the native units of the planck function
        native_bolflux = (
            scale * const.sigma_sb * self.temperature ** 4 / np.pi
        )
        # return in more "astro" units
        return native_bolflux.to(u.erg / (u.cm ** 2 * u.s))

    @property
    def lambda_max(self):
        """Peak wavelength when the curve is expressed as power density."""
        return const.b_wien / self.temperature

    @property
    def nu_max(self):
        """Peak frequency when the curve is expressed as power density."""
        return 2.8214391 * const.k_B * self.temperature / const.h
