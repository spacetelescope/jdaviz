import warnings

from astropy import units as u
from astropy.utils.decorators import deprecated
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

    def load_data(self, data, data_label=None, format=None, show_in_viewer=True,
                  concat_by_file=False, cache=None, local_path=None, timeout=None,
                  load_as_list=False):
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
        cache : None, bool, or str
            Cache the downloaded file if the data are retrieved by a query
            to a URL or URI.
        local_path : str, optional
            Cache remote files to this path. This is only used if data is
            requested from `astroquery.mast`.
        timeout : float, optional
            If downloading from a remote URI, set the timeout limit for
            remote requests in seconds (passed to
            `~astropy.utils.data.download_file` or
            `~astroquery.mast.Conf.timeout`).
        """
        super().load_data(data,
                          parser_reference='specviz-spectrum1d-parser',
                          data_label=data_label,
                          format=format,
                          show_in_viewer=show_in_viewer,
                          concat_by_file=concat_by_file,
                          cache=cache,
                          local_path=local_path,
                          timeout=timeout,
                          load_as_list=load_as_list)

    @deprecated(since="4.1", alternative="subset_tools.get_regions")
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

    @deprecated(since="4.2", alternative="viewers['spectrum-viewer'].set_limits")
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

    @deprecated(since="4.2", alternative="viewers['spectrum-viewer'].set_limits")
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
                min_val = min_val.to_value(axis.unit)
            # If auto, set to min axis wavelength value
            elif min_val == "auto":
                min_val = min(axis).value

            scale.min = float(min_val)
        if max_val is not None:
            # If user's value has a unit, convert it to the current axis' units
            if isinstance(max_val, u.Quantity):
                # Convert user's value to axis' units
                max_val = max_val.to_value(axis.unit)
            # If auto, set to max axis wavelength value
            elif max_val == "auto":
                max_val = max(axis).value

            scale.max = float(max_val)

    @deprecated(since="4.2", alternative="viewers['spectrum-viewer'].reset_limits")
    def autoscale_x(self):
        """Sets the x-axis limits to the min/max of the reference data

        """
        self.x_limits("auto", "auto")

    @deprecated(since="4.2", alternative="viewers['spectrum-viewer'].reset_limits")
    def autoscale_y(self):
        """Sets the y-axis limits to the min/max of the reference data

        """
        self.y_limits("auto", "auto")

    @deprecated(since="4.2", alternative="viewers['spectrum-viewer'].set_limits")
    def flip_x(self):
        """Flips the current limits of the x-axis

        """
        scale = self.app.get_viewer(self._default_spectrum_viewer_reference_name).scale_x
        self.x_limits(x_min=scale.max, x_max=scale.min)

    @deprecated(since="4.2", alternative="viewers['spectrum-viewer'].set_limits")
    def flip_y(self):
        """Flips the current limits of the y-axis

        """
        scale = self.app.get_viewer(self._default_spectrum_viewer_reference_name).scale_y
        self.y_limits(y_min=scale.max, y_max=scale.min)

    @deprecated(since="4.2", alternative="viewers['spectrum-viewer'].set_tick_format")
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

        sv = self.viewers[self._default_spectrum_viewer_reference_name]
        sv.set_tick_format(fmt, axis=['x', 'y'][axis])

    def get_data(self, data_label=None, spectral_subset=None, cls=None,
                 use_display_units=False, apply_slider_redshift="Warn"):
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
        apply_slider_redshift : bool, optional
            Whether to apply the redshift slider value to the output spectra. If set to "Warn",
            a warning will be issued if the redshift slider is not set to 0. To avoid seeing this
            warning, explicitly set the apply_slider_redshift keyword option to True or False.

        Returns
        -------
        data : cls
            Data is returned as type cls with subsets applied.

        """
        data = self._get_data(data_label=data_label, spectral_subset=spectral_subset,
                              cls=cls, use_display_units=use_display_units)

        if apply_slider_redshift and isinstance(data, Spectrum1D):
            return _apply_redshift_to_spectra(data, self._redshift)
        return data

    def get_spectra(self, data_label=None, spectral_subset=None, apply_slider_redshift="Warn"):
        """Returns the current data loaded into the main viewer

        Parameters
        ----------
        data_label : str, optional
            Provide a label to retrieve a specific data set from data_collection.
        spectral_subset : str, optional
            Spectral subset applied to data.
        apply_slider_redshift : bool, optional
            Whether to apply the redshift slider value to the output spectra. If set to "Warn",
            a warning will be issued if the redshift slider is not set to 0. To avoid seeing this
            warning, explicitly set the apply_slider_redshift keyword option to True or False.

        Returns
        -------
        dict: dictionary of Spectrum1D objects
        """
        sv = self.viewers[self._default_spectrum_viewer_reference_name]
        spectra_labels = sv.data_menu.data_labels_loaded if data_label is None else [data_label]
        subset_labels = sv.data_menu.subset_labels_visible if spectral_subset is None else [spectral_subset]  # noqa

        spectra = {}
        for spec_label in spectra_labels:
            spectra[spec_label] = self.get_data(data_label=spec_label,
                                                cls=Spectrum1D,
                                                apply_slider_redshift=apply_slider_redshift)
            for subset_label in subset_labels:
                spectrum = self.get_data(data_label=spec_label,
                                         spectral_subset=subset_label,
                                         cls=Spectrum1D,
                                         apply_slider_redshift=apply_slider_redshift)
                spectra[f"{spec_label} ({subset_label})"] = spectrum
        return spectra
