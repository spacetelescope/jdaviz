import warnings
import operator

from astropy import units as u
from astropy.utils.decorators import deprecated
from specutils import SpectralRegion, Spectrum1D
from glue.core.subset import CompositeSubsetState, InvertState

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
        super().load_data(data,
                          parser_reference='specviz-spectrum1d-parser',
                          data_label=data_label,
                          format=format,
                          show_in_viewer=show_in_viewer,
                          concat_by_file=concat_by_file)

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

    def _remove_duplicate_bounds(self, spec_regions):
        regions_no_dups = None

        for region in spec_regions:
            if not regions_no_dups:
                regions_no_dups = region
            elif region.bounds not in regions_no_dups.subregions:
                regions_no_dups += region
        return regions_no_dups

    def get_sub_regions(self, subset_state, units):
        if isinstance(subset_state, CompositeSubsetState):
            if subset_state and hasattr(subset_state, "state2") and subset_state.state2:
                one = self.get_sub_regions(subset_state.state1, units)
                two = self.get_sub_regions(subset_state.state2, units)

                if isinstance(subset_state.state2, InvertState):
                    # This covers the REMOVE subset mode

                    # As an example for how this works:
                    # a = SpectralRegion(4 * u.um, 7 * u.um) + SpectralRegion(9 * u.um, 11 * u.um)
                    # b = SpectralRegion(5 * u.um, 6 * u.um)
                    # After running the following code with a as one and b as two:
                    # Spectral Region, 3 sub-regions:
                    #   (4.0 um, 5.0 um)    (6.0 um, 7.0 um)    (9.0 um, 11.0 um)
                    new_spec = None
                    for sub in one:
                        if not new_spec:
                            new_spec = two.invert(sub.lower, sub.upper)
                        else:
                            new_spec += two.invert(sub.lower, sub.upper)
                    return new_spec
                elif subset_state.op is operator.and_:
                    # This covers the AND subset mode

                    # Example of how this works:
                    # a = SpectralRegion(4 * u.um, 7 * u.um)
                    # b = SpectralRegion(5 * u.um, 6 * u.um)
                    #
                    # b.invert(a.lower, a.upper)
                    # Spectral Region, 2 sub-regions:
                    #   (4.0 um, 5.0 um)   (6.0 um, 7.0 um)
                    return two.invert(one.lower, one.upper)
                elif subset_state.op is operator.or_:
                    # This covers the ADD subset mode
                    return one + two
                elif subset_state.op is operator.xor:
                    # This covers the XOR case which is currently not working
                    return None
                else:
                    return None
            else:
                return self.get_sub_regions(subset_state.state1, units)
        elif subset_state is not None:
            return SpectralRegion(subset_state.lo * units, subset_state.hi * units)

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
        dc = self.app.data_collection
        subsets = dc.subset_groups
        # TODO: Use global display units
        units = dc[0].data.coords.spectral_axis.unit

        all_subsets = {}

        for subset in subsets:
            label = subset.label
            all_subsets[label] = self._remove_duplicate_bounds(
                self.get_sub_regions(subset.subset_state, units))

        return all_subsets

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


@deprecated('3.2', alternative='Specviz')
class SpecViz(Specviz):
    """This class is pending deprecation. Please use `Specviz` instead."""
    pass
