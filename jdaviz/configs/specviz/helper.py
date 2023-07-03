import warnings

from astropy import units as u
from astropy.utils.decorators import deprecated_renamed_argument, deprecated
from regions.core.core import Region
from glue.core.subset_group import GroupedSubset
from specutils import SpectralRegion, Spectrum1D

from jdaviz.core.helpers import ConfigHelper
from jdaviz.core.events import RedshiftMessage
from jdaviz.configs.default.plugins.line_lists.line_list_mixin import LineListMixin

__all__ = ['Specviz']


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

    @deprecated(since="3.6", alternative="load_data")
    def load_spectrum(self, data, data_label=None, format=None, show_in_viewer=True,
                      concat_by_file=False):
        """
        Loads a data file or `~specutils.Spectrum1D` object into Specviz.

        Parameters
        ----------
        data : str, `~specutils.Spectrum1D`, or `~specutils.SpectrumList`
            Spectrum1D, SpectrumList, or path to compatible data file.
        data_label : str
            The Glue data label found in the ``DataCollection``.
        format : str
            Loader format specification used to indicate data format in
            `~specutils.Spectrum1D.read` io method.
        show_in_viewer : bool
            Show data in viewer(s).
        concat_by_file : bool
            If True and there is more than one available extension, concatenate
            the extensions within each spectrum file passed to the parser and
            add a concatenated spectrum to the data collection.
        """
        self.load_data(data, data_label, format, show_in_viewer, concat_by_file)

    def load_data(self, data, data_label=None, format=None, show_in_viewer=True,
                  concat_by_file=False):
        """
        Load data into Specviz.

        Parameters
        ----------
        data : str, `~specutils.Spectrum1D`, or `~specutils.SpectrumList`
            Spectrum1D, SpectrumList, or path to compatible data file.
        data_label : str
            The Glue data label found in the ``DataCollection``.
        format : str
            Loader format specification used to indicate data format in
            `~specutils.Spectrum1D.read` io method.
        show_in_viewer : bool
            Show data in viewer(s).
        concat_by_file : bool
            If True and there is more than one available extension, concatenate
            the extensions within each spectrum file passed to the parser and
            add a concatenated spectrum to the data collection.
        """
        super().load_data(data,
                          parser_reference='specviz-spectrum1d-parser',
                          data_label=data_label,
                          format=format,
                          show_in_viewer=show_in_viewer,
                          concat_by_file=concat_by_file)

    @deprecated_renamed_argument("subset_to_apply", "spectral_subset", "3.6")
    def get_spectra(self, data_label=None, spectral_subset=None, apply_slider_redshift="Warn"):
        """Returns the current data loaded into the main viewer

        """
        spectra = {}
        # Just to save line length
        get_data_method = self.app._jdaviz_helper.get_data
        viewer = self.app.get_viewer(self._default_spectrum_viewer_reference_name)
        function_kwargs = {'function': getattr(viewer.state, "function")} if self.app.config == 'cubeviz' else {}  # noqa
        all_subsets = self.app.get_subsets(object_only=True)

        if data_label is not None:
            spectrum = get_data_method(data_label=data_label,
                                       spectral_subset=spectral_subset,
                                       cls=Spectrum1D)
            spectra[data_label] = spectrum
        else:
            for layer_state in viewer.state.layers:
                lyr = layer_state.layer
                if spectral_subset is not None:
                    if lyr.label == spectral_subset:
                        spectrum = get_data_method(data_label=lyr.data.label,
                                                   spectral_subset=spectral_subset,
                                                   cls=Spectrum1D,
                                                   **function_kwargs)
                        spectra[lyr.data.label] = spectrum
                    else:
                        continue
                else:
                    if (isinstance(lyr, GroupedSubset) and lyr.label in all_subsets.keys() and
                            isinstance(all_subsets[lyr.label][0], Region)):
                        spectrum = get_data_method(data_label=lyr.data.label,
                                                   spatial_subset=lyr.label,
                                                   cls=Spectrum1D,
                                                   **function_kwargs)
                        spectra[f'{lyr.data.label} ({lyr.label})'] = spectrum
                    elif (isinstance(lyr, GroupedSubset) and lyr.label in all_subsets.keys() and
                            isinstance(all_subsets[lyr.label], SpectralRegion)):
                        spectrum = get_data_method(data_label=lyr.data.label,
                                                   spectral_subset=lyr.label,
                                                   cls=Spectrum1D,
                                                   **function_kwargs)
                        spectra[f'{lyr.data.label} ({lyr.label})'] = spectrum
                    else:
                        spectrum = get_data_method(data_label=lyr.label,
                                                   cls=Spectrum1D,
                                                   **function_kwargs)
                        spectra[lyr.label] = spectrum

        if not apply_slider_redshift:
            if data_label is not None:
                return spectra[data_label]
            return spectra
        else:
            output_spectra = {}
            # We need to create new Spectrum1D outputs with the redshifts set
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

    def get_spectral_regions(self, use_display_units=False):
        """
        A simple wrapper around the app-level call to retrieve only spectral
        subsets, which are now returned as SpectralRegions by default.

        Parameters
        ----------
        use_display_units : bool, optional
            Whether to convert to the display units defined in the
            :ref:`Unit Conversion <unit-conversion>` plugin.

        Returns
        -------
        spec_regs : dict
            Mapping from the names of the subsets to the subsets expressed
            as `specutils.SpectralRegion` objects.
        """
        return self.app.get_subsets(spectral_only=True, use_display_units=use_display_units)

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
        flux_axis = self.get_spectra(ref_index, apply_slider_redshift=False).flux
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

    def get_data(self, data_label=None, spectral_subset=None, cls=None,
                 use_display_units=False, **kwargs):
        """
        Returns data with name equal to data_label of type cls with subsets applied from
        spectral_subset.

        Parameters
        ----------
        data_label : str, optional
            Provide a label to retrieve a specific data set from data_collection.
        spectral_subset : str, optional
            Spectral subset applied to data.
        cls : `~specutils.Spectrum1D`, optional
            The type that data will be returned as.
        use_display_units: bool, optional
            Whether to convert to the display units defined in the <unit-conversion> plugin.

        Returns
        -------
        data : cls
            Data is returned as type cls with subsets applied.

        """
        spatial_subset = kwargs.pop("spatial_subset", None)
        function = kwargs.pop("function", None)
        if len(kwargs) > 0:
            raise ValueError(f'kwargs {[x for x in kwargs.keys()]} are not valid')

        if self.app.config == 'cubeviz':
            # then this is a specviz instance inside cubeviz and we want to default to the
            # viewer's collapse function
            default_sp_viewer = self.app.get_viewer(self._default_spectrum_viewer_reference_name)
            if function is True or function is None:
                function = getattr(default_sp_viewer.state, 'function', None)

            if cls is None:
                cls = Spectrum1D
        elif spatial_subset or function:
            raise ValueError('kwargs spatial subset and function are not valid in specviz')
        else:
            spatial_subset = None
            function = None

        return self._get_data(data_label=data_label, spatial_subset=spatial_subset,
                              spectral_subset=spectral_subset, function=function,
                              cls=cls, use_display_units=use_display_units)
