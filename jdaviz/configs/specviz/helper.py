import warnings

from astropy import units as u
from specutils import SpectralRegion, Spectrum1D

from jdaviz.core.helpers import ConfigHelper
from jdaviz.core.events import RedshiftMessage
from jdaviz.configs.default.plugins.line_lists.line_list_mixin import LineListMixin

__all__ = ['Specviz', 'SpecViz']


def _apply_redshift_to_spectra(spectra, redshift):

    flux = spectra.flux
    # This is a hack around inability to input separate redshift with
    # a SpectralAxis instance in Spectrum1D
    spaxis = spectra.spectral_axis.value * spectra.spectral_axis.unit
    mask = spectra.mask
    uncertainty = spectra.uncertainty
    output_spectra = Spectrum1D(flux, spectral_axis=spaxis,
                                redshift=redshift, mask=mask,
                                uncertainty=uncertainty)

    return output_spectra


class Specviz(ConfigHelper, LineListMixin):
    """Specviz Helper class."""

    _default_configuration = "specviz"
    _default_spectrum_viewer_reference_name = "spectrum-viewer"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Listen for new redshifts from the redshift slider
        self.app.hub.subscribe(self, RedshiftMessage,
                               handler=self._redshift_listener)

    def load_spectrum(self, data, data_label=None, format=None, show_in_viewer=True,
                      spectrum_viewer_reference_name=None):

        # If viewer reference name is not specified and
        # the default viewer is available, use default
        if spectrum_viewer_reference_name is None:
            if (self._default_spectrum_viewer_reference_name in
                    self.app.get_viewer_reference_names()):
                spectrum_viewer_reference_name = self._default_spectrum_viewer_reference_name

            # If viewer reference name is not specified and default is unavailable,
            # use first spectrum viewer without loaded data:
            else:
                spectrum_viewer_reference_name = self.app._get_first_viewer_reference_name(
                    require_spectrum_viewer=True, require_no_selected_data=True
                )

        super().load_data(data,
                          parser_reference='specviz-spectrum1d-parser',
                          data_label=data_label,
                          format=format,
                          show_in_viewer=show_in_viewer)

    def get_spectra(self, data_label=None, apply_slider_redshift="Warn"):
        """Returns the current data loaded into the main viewer

        """
        spectra = self.app.get_data_from_viewer(
            self._default_spectrum_viewer_reference_name, data_label=data_label
        )
        if not apply_slider_redshift:
            return spectra
        else:
            output_spectra = {}
            # We need to create new Spectrum1D outputs with the redshifts set
            if data_label is not None:
                spectra = {data_label: spectra}
            for key in spectra.keys():
                output_spectra[key] = _apply_redshift_to_spectra(spectra[key], self._redshift)

            if apply_slider_redshift == "Warn":
                warnings.warn("Applying the value from the redshift "
                              "slider to the output spectra. To avoid seeing this "
                              "warning, explicitly set the apply_slider_redshift "
                              "keyword option to True or False.")

            if data_label is not None:
                output_spectra = output_spectra[data_label]

            return output_spectra

    def get_spectral_regions(self):
        """
        A simple wrapper around the app-level call to retrieve only spectral
        subsets, which are now returned as SpectralRegions by default.

        Returns
        -------
        spec_regs : dict
            Mapping from the names of the subsets to the subsets expressed
            as `specutils.SpectralRegion` objects.
        """
        return self.app.get_subsets_from_viewer(
            self._default_spectrum_viewer_reference_name, subset_type="spectral"
        )

    def x_limits(self, x_min=None, x_max=None):
        """Sets the limits of the x-axis

        Parameters
        ----------
        x_min
            The lower bound of the axis. Can also be a Specutils SpectralRegion
        x_max
            The upper bound of the axis
        """
        scale = self.app.get_viewer(self._default_spectrum_viewer_reference_name).scale_x
        if x_min is None and x_max is None:
            return scale

        # Retrieve the spectral axis
        ref_index = getattr(
            self.app.get_viewer(self._default_spectrum_viewer_reference_name).state.reference_data,
            "label", None
        )
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
        scale = self.app.get_viewer(self._default_spectrum_viewer_reference_name).scale_y
        if y_min is None and y_max is None:
            return scale

        # Retrieve the flux axis
        ref_index = self.app.get_viewer(
            self._default_spectrum_viewer_reference_name
        ).state.reference_data.label
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
            # If auto, set to min axis wavelength value
            elif min_val == "auto":
                min_val = min(axis).value

            scale.min = float(min_val)
        if max_val is not None:
            # If user's value has a unit, convert it to the current axis' units
            if isinstance(max_val, u.Quantity):
                # Convert user's value to axis' units
                max_val = max_val.to(axis.unit).value
            # If auto, set to max axis wavelength value
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
        scale = self.app.get_viewer(self._default_spectrum_viewer_reference_name).scale_x
        self.x_limits(x_min=scale.max, x_max=scale.min)

    def flip_y(self):
        """Flips the current limits of the y-axis

        """
        scale = self.app.get_viewer(self._default_spectrum_viewer_reference_name).scale_y
        self.y_limits(y_min=scale.max, y_max=scale.min)

    def set_spectrum_tick_format(self, fmt, axis=None):
        """
        Manually set the tick format of one of the axes of the profile viewer.

        Parameters
        ----------
        fmt : str
            Format of tick marks in the spectrum viewer.
            For example, ``'0.1e'`` to set scientific notation or ``'0.2f'`` to turn it off.
        axis : {0, 1}
            The spectrum viewer data axis.
            Axis 1 corresponds to the Y-axis and 0 to the X-axis.

        """
        if axis not in [0, 1]:
            warnings.warn("Please use either 0 or 1 for the axis value")
            return

        # Examples of values for fmt are '0.1e' or '0.2f'
        self.app.get_viewer(
            self._default_spectrum_viewer_reference_name
        ).figure.axes[axis].tick_format = fmt


# TODO: Officially deprecate this with coordination with JDAT notebooks team.
# For backward compatibility only.
class SpecViz(Specviz):
    """This class is pending deprecation. Please use `Specviz` instead."""
    pass
