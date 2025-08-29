import warnings

from astropy import units as u
from astropy.utils.decorators import deprecated
from regions.core.core import Region
from glue.core.subset_group import GroupedSubset
from specutils import SpectralRegion, Spectrum, SpectrumList, SpectrumCollection

from jdaviz.core.helpers import ConfigHelper
from jdaviz.core.events import RedshiftMessage
from jdaviz.configs.default.plugins.line_lists.line_list_mixin import LineListMixin

__all__ = ['Specviz']


def _apply_redshift_to_spectra(spectra, redshift):

    flux = spectra.flux
    # This is a hack around inability to input separate redshift with
    # a SpectralAxis instance in Spectrum
    spaxis = spectra.spectral_axis.value * spectra.spectral_axis.unit
    mask = spectra.mask
    uncertainty = spectra.uncertainty
    output_spectra = Spectrum(flux, spectral_axis=spaxis,
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
        # Temporary during deconfigging (until _load exposed to all configs)
        self.load = self._load

    @deprecated(since="4.3", alternative="load")
    def load_data(self, data, data_label=None, format=None, show_in_viewer=True,
                  concat_by_file=False, cache=None, local_path=None, timeout=None,
                  load_as_list=False, exposures=None, sources=None, load_all=False):
        """
        Load data into Specviz.

        Parameters
        ----------
        data : str, `~specutils.Spectrum`, or `~specutils.SpectrumList`
            Spectrum, SpectrumList, or path to compatible data file.
        data_label : str
            The Glue data label found in the ``DataCollection``.
        format : str
            Loader format specification used to indicate data format in
            `~specutils.Spectrum.read` io method.
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
        if format is not None:
            raise NotImplementedError("format is ignored and will be removed in a future release")

        if load_as_list and concat_by_file:
            raise ValueError("Cannot set both load_as_list and concat_by_file")

        load_kwargs = {}
        if cache is not None:
            load_kwargs['cache'] = cache
        if timeout is not None:
            load_kwargs['timeout'] = timeout
        if local_path is not None:
            load_kwargs['local_path'] = local_path
        if sources is not None:
            load_kwargs['sources'] = sources
        if exposures is not None:
            load_kwargs['exposures'] = exposures

        if isinstance(data, (SpectrumList, SpectrumCollection)) and isinstance(data_label, list):
            if len(data_label) != len(data):
                raise ValueError(f"Length of data labels list ({len(data_label)}) is different"
                                 f" than length of list of data ({len(data)})")
            # new infrastructure doesn't support passing a list, but we'll
            # wrap it for now during deprecation period
            for spec, label in zip(data, data_label):
                self.load_data(spec, data_label=label,
                               show_in_viewer=show_in_viewer,
                               **load_kwargs)
            return

        if load_as_list:
            format = '1D Spectrum List'
        elif concat_by_file:
            format = '1D Spectrum Concatenated'
        elif (isinstance(data, (SpectrumList, SpectrumCollection))
                or (isinstance(data, Spectrum) and len(data.shape) == 2)):
            format = '1D Spectrum List'
        else:
            format = '1D Spectrum'
        if data_label is not None:
            data_label = self.app.return_unique_name(data_label)
        self.load(data, format=format,
                  data_label=data_label,
                  viewer='*' if show_in_viewer else [],
                  **load_kwargs)

    @property
    def _spectrum_viewer(self):
        viewer_reference = self.app._get_first_viewer_reference_name(
            require_spectrum_viewer=True
        )
        if viewer_reference is None:
            return None

        return self.app.get_viewer(viewer_reference)

    def get_spectra(self, data_label=None, spectral_subset=None, apply_slider_redshift="Warn"):
        """Returns the current data loaded into the main viewer

        """
        spectra = {}
        # Just to save line length
        get_data_method = self.app._jdaviz_helper.get_data
        viewer = self._spectrum_viewer
        if viewer is None:
            return spectra
        all_subsets = self.app.get_subsets(object_only=True)

        if data_label is not None:
            spectrum = get_data_method(data_label=data_label,
                                       spectral_subset=spectral_subset,
                                       cls=Spectrum)
            spectra[data_label] = spectrum
        else:
            for layer_state in viewer.state.layers:
                lyr = layer_state.layer
                if spectral_subset is not None:
                    if lyr.label == spectral_subset:
                        spectrum = get_data_method(data_label=lyr.data.label,
                                                   spectral_subset=spectral_subset,
                                                   cls=Spectrum)
                        spectra[lyr.data.label] = spectrum
                    else:
                        continue
                elif (isinstance(lyr, GroupedSubset) and lyr.label in all_subsets.keys() and
                        isinstance(all_subsets[lyr.label][0], Region)):
                    # spatial subsets appear as automatically extracted entries, we can skip
                    # the layer representing the subset itself.
                    continue
                elif (isinstance(lyr, GroupedSubset) and lyr.label in all_subsets.keys() and
                        isinstance(all_subsets[lyr.label], SpectralRegion)):
                    spectrum = get_data_method(data_label=lyr.data.label,
                                               spectral_subset=lyr.label,
                                               cls=Spectrum)
                    spectra[f'{lyr.data.label} ({lyr.label})'] = spectrum
                else:
                    spectrum = get_data_method(data_label=lyr.label,
                                               cls=Spectrum)
                    spectra[lyr.label] = spectrum

        if not apply_slider_redshift:
            if data_label is not None:
                return spectra[data_label]
            return spectra
        else:
            output_spectra = {}
            # We need to create new Spectrum outputs with the redshifts set
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

    @deprecated(since="4.2", alternative="viewers['1D Spectrum'].set_limits")
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

    @deprecated(since="4.2", alternative="viewers['1D Spectrum'].set_limits")
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

    @deprecated(since="4.2", alternative="viewers['1D Spectrum'].reset_limits")
    def autoscale_x(self):
        """Sets the x-axis limits to the min/max of the reference data

        """
        self.x_limits("auto", "auto")

    @deprecated(since="4.2", alternative="viewers['1D Spectrum'].reset_limits")
    def autoscale_y(self):
        """Sets the y-axis limits to the min/max of the reference data

        """
        self.y_limits("auto", "auto")

    @deprecated(since="4.2", alternative="viewers['1D Spectrum'].set_limits")
    def flip_x(self):
        """Flips the current limits of the x-axis

        """
        scale = self.app.get_viewer(self._default_spectrum_viewer_reference_name).scale_x
        self.x_limits(x_min=scale.max, x_max=scale.min)

    @deprecated(since="4.2", alternative="viewers['1D Spectrum'].set_limits")
    def flip_y(self):
        """Flips the current limits of the y-axis

        """
        scale = self.app.get_viewer(self._default_spectrum_viewer_reference_name).scale_y
        self.y_limits(y_min=scale.max, y_max=scale.min)

    @deprecated(since="4.2", alternative="viewers['1D Spectrum'].set_tick_format")
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

    def get_data(self, data_label=None, spectral_subset=None, cls=Spectrum,
                 use_display_units=False):
        """
        Returns data with name equal to data_label of type cls with subsets applied from
        spectral_subset.

        Parameters
        ----------
        data_label : str, optional
            Provide a label to retrieve a specific data set from data_collection.
        spectral_subset : str, optional
            Spectral subset applied to data.
        cls : `~specutils.Spectrum`, optional
            The type that data will be returned as.
        use_display_units: bool, optional
            Whether to convert to the display units defined in the <unit-conversion> plugin.

        Returns
        -------
        data : cls
            Data is returned as type cls with subsets applied.

        """
        return self._get_data(data_label=data_label, spectral_subset=spectral_subset,
                              cls=cls, use_display_units=use_display_units)
