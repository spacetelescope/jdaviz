import logging

import astropy.units as u
from specutils import SpectralRegion, Spectrum1D

from jdaviz.core.helpers import ConfigHelper
from jdaviz.core.events import RedshiftMessage
from ..default.plugins.line_lists.line_list_mixin import LineListMixin


class SpecViz(ConfigHelper, LineListMixin):
    """
    SpecViz Helper class

    """

    _default_configuration = "specviz"
    _redshift = 0

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Listen for new redshifts from the redshift slider
        self.app.hub.subscribe(self, RedshiftMessage,
                               handler=self._redshift_listener)

    def load_spectrum(self, data, data_label=None, format=None, show_in_viewer=True):
        super().load_data(data,
                          'specviz-spectrum1d-parser',
                          data_label=data_label,
                          format=format,
                          show_in_viewer=show_in_viewer)

    def get_spectra(self, data_label=None, apply_slider_redshift="Warn"):
        """Returns the current data loaded into the main viewer

        """
        spectra = self.app.get_data_from_viewer("spectrum-viewer", data_label=data_label)
        if not apply_slider_redshift:
            return spectra
        else:
            output_spectra = {}
            # We need to create new Spectrum1D outputs with the redshifts set
            if data_label is not None:
                spectra = {data_label: spectra}
            for key in spectra.keys():
                flux = spectra[key].flux
                # This is a hack around inability to input separate redshift with
                # a SpectralAxis instance in Spectrum1D
                spaxis = spectra[key].spectral_axis.value * spectra[key].spectral_axis.unit
                mask = spectra[key].mask
                uncertainty = spectra[key].uncertainty
                output_spectra[key] = Spectrum1D(flux, spectral_axis=spaxis,
                                                 redshift=self._redshift, mask=mask,
                                                 uncertainty=uncertainty)
            if apply_slider_redshift == "Warn":
                logging.warning("Warning: Applying the value from the redshift "
                                "slider to the output spectra. To avoid seeing this "
                                "warning, explicitly set the apply_slider_redshift "
                                "argument to True or False.")

            if data_label is not None:
                output_spectra = output_spectra[data_label]

            return output_spectra

    def get_spectral_regions(self):
        """
        Retrieves glue subset objects from the spectrum viewer and converts
        them to `~specutils.SpectralRegion` objects.

        Returns
        -------
        spec_regs : dict
            Mapping from the names of the subsets to the subsets expressed
            as `specutils.SpectralRegion` objects.
        """
        regions = self.app.get_subsets_from_viewer("spectrum-viewer")

        spec_regs = {}

        for name, reg in regions.items():
            unit = reg.meta.get("spectral_axis_unit", u.Unit("Angstrom"))
            spec_reg = SpectralRegion.from_center(reg.center.x * unit,
                                                  reg.width * unit)

            spec_regs[name] = spec_reg

        return spec_regs

    def x_limits(self, x_min=None, x_max=None):
        """Sets the limits of the x-axis

        Parameters
        ----------
        x_min
            The lower bound of the axis. Can also be a Specutils SpectralRegion
        x_max
            The upper bound of the axis
        """
        scale = self.app.get_viewer("spectrum-viewer").scale_x
        if x_min is None and x_max is None:
            return scale

        # Retrieve the spectral axis
        ref_index = self.app.get_viewer("spectrum-viewer").state.reference_data.label
        ref_spec = self.get_spectra(ref_index, apply_slider_redshift=False)
        self._set_scale(scale, ref_spec.spectral_axis, x_min, x_max)

    def y_limits(self, y_min=None, y_max=None):
        """Sets the limits of the y-axis

        Parameters
        ----------
        y_min
            The lower bound of the axis. Can also be a Specutils SpectralRegion
        y_max
            The upper bound of the axis
        """
        scale = self.app.get_viewer("spectrum-viewer").scale_y
        if y_min is None and y_max is None:
            return scale

        # Retrieve the flux axis
        ref_index = self.app.get_viewer("spectrum-viewer").state.reference_data.label
        flux_axis = self.get_spectra(ref_index).flux
        self._set_scale(scale, flux_axis, y_min, y_max)

    def _set_scale(self, scale, axis, min_val=None, max_val=None):
        """Internal helper method to set the bqplot scale

        Parameters
        ----------
        scale
            The Bqplot viewer scale
        axis
            The Specutils data axis
        min_val
            The lower bound of the axis to set. Can also be a Specutils SpectralRegion
        max_val
            The upper bound of the axis to set
        """
        if min_val is not None:
            # If SpectralRegion, set limits to region's lower and upper bounds
            if isinstance(min_val, SpectralRegion):
                return self._set_scale(scale, axis, min_val.lower, min_val.upper)
            # If user's value has a unit, convert it to the current axis' units
            elif isinstance(min_val, u.Quantity):
                # Convert user's value to axis' units
                min_val = min_val.to(axis.unit).value
            # If auto, set to min_valimum wavelength value
            elif min_val == "auto":
                min_val = min(axis).value

            scale.min = float(min_val)
        if max_val is not None:
            # If user's value has a unit, convert it to the current axis' units
            if isinstance(max_val, u.Quantity):
                # Convert user's value to axis' units
                max_val = max_val.to(axis.unit).value
            # If auto, set to max_valimum wavelength value
            elif max_val == "auto":
                max_val = max(axis).value

            scale.max = float(max_val)

    def autoscale_x(self):
        """Sets the x-axis limits to the min/max of the reference data

        """
        self.x_limits("auto", "auto")

    def autoscale_y(self):
        """Sets the y-axis limits to the min/max of the reference data

        """
        self.y_limits("auto", "auto")

    def flip_x(self):
        """Flips the current limits of the x-axis

        """
        scale = self.app.get_viewer("spectrum-viewer").scale_x
        self.x_limits(x_min=scale.max, x_max=scale.min)

    def flip_y(self):
        """Flips the current limits of the y-axis

        """
        scale = self.app.get_viewer("spectrum-viewer").scale_y
        self.y_limits(y_min=scale.max, y_max=scale.min)

    def show(self):
        self.app

    def set_redshift_slider_bounds(self, lower=None, upper=None, step=None):
        '''
        Set the upper, lower, or both bounds of the redshift slider. Note
        that this does not do any sanity checks on the numbers provided based
        on whether the slider is set to Redshift or Radial Velocity.
        '''
        if lower is not None:
            msg = RedshiftMessage("slider_min", lower, sender=self)
            self.app.hub.broadcast(msg)
        if upper is not None:
            msg = RedshiftMessage("slider_max", upper, sender=self)
            self.app.hub.broadcast(msg)
        if step is not None:
            msg = RedshiftMessage("slider_step", step, sender=self)
            self.app.hub.broadcast(msg)

    def set_redshift(self, new_redshift):
        '''
        Apply a redshift to any loaded spectral lines and data. Also updates
        the value shown in the slider.
        '''
        msg = RedshiftMessage("redshift", new_redshift, sender=self)
        self.app.hub.broadcast(msg)

    def _redshift_listener(self, msg):
        '''Save new redshifts (including from the helper itself)'''
        if msg.param == "redshift":
            self._redshift = msg.value
