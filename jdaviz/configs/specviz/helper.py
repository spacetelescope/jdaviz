import base64
import pathlib
import uuid
from astropy import units as u
from specutils import Spectrum1D, SpectrumCollection, SpectralRegion

import astropy.units as u
from specutils import Spectrum1D, SpectrumCollection, SpectralRegion

from jdaviz.core.helpers import ConfigHelper


class SpecViz(ConfigHelper):
    """SpecViz Helper class"""

    _default_configuration = "specviz"

    def load_data(self, data, data_label=None, format=None, show_in_viewer=True):
        """
        Loads a data file or `~specutils.Spectrum1D` object into SpecViz.

        Parameters
        ----------
        data : str or `~specutils.Spectrum1D`
            Spectrum1D spectra, or path to compatible data file.
        data_label : str
            The Glue data label found in the ``DataCollection``.
        format : str
            Loader format specification used to indicate data format in
            `~specutils.Spectrum1D.read` io method.
        """
        # If no data label is assigned, give it a unique identifier
        if not data_label:
            data_label = "specviz_data|" + str(
                base64.b85encode(uuid.uuid4().bytes), "utf-8"
            )
        # If data provided is a path, try opening into a Spectrum1D object
        try:
            path = pathlib.Path(data)

            if path.is_file():
                data = Spectrum1D.read(path, format=format)
            else:
                raise FileNotFoundError("No such file: " + path)
        # If not, it must be a Spectrum1D object. Otherwise, it's unsupported
        except TypeError:
            if type(data) is SpectrumCollection:
                raise TypeError(
                    "SpectrumCollection detected. Please provide a Spectrum1D"
                )
            elif type(data) is not Spectrum1D:
                raise TypeError("Data is not a Spectrum1D object or compatible file")
        self.app.add_data(data, data_label)
        if show_in_viewer:
            self.app.add_data_to_viewer("spectrum-viewer", data_label)

    def get_spectra(self, data_label=None):
        """Returns the current data loaded into the main viewer"""
        return self.app.get_data_from_viewer("spectrum-viewer", data_label=data_label)

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
            spec_reg = SpectralRegion.from_center(reg.center.x * unit, reg.width * unit)

            spec_regs[name] = spec_reg

        return spec_regs

    def x_limits(self, x_min=None, x_max=None):
        """Sets the limits of the x-axis

        :param x_min: The lower bound of the axis. Can also be a
            Specutils SpectralRegion
        :param x_max: The upper bound of the axis
        """
        scale = self.app.get_viewer("spectrum-viewer").scale_x
        if not x_min and not x_max:
            return scale
        else:
            # Retrieve the spectral axis
            ref_index = self.app.get_viewer(
                "spectrum-viewer"
            ).state.reference_data.label
            spectral_axis = self.get_spectra(ref_index).get(ref_index).spectral_axis
            self._set_scale(scale, spectral_axis, x_min, x_max)

    def y_limits(self, y_min=None, y_max=None):
        """Sets the limits of the y-axis

        :param y_min: The lower bound of the axis. Can also be a
            Specutils SpectralRegion
        :param y_max: The upper bound of the axis
        """
        scale = self.app.get_viewer("spectrum-viewer").scale_y
        if not y_min and not y_max:
            return scale
        else:
            # Retrieve the flux axis
            ref_index = self.app.get_viewer(
                "spectrum-viewer"
            ).state.reference_data.label
            flux_axis = self.get_spectra(ref_index).get(ref_index).flux
            self._set_scale(scale, flux_axis, y_min, y_max)

    def _set_scale(self, scale, axis, min_val=None, max_val=None):
        """Internal helper method to set the bqplot scale

        :param scale: The Bqplot viewer scale
        :param axis: The Specutils data axis
        :param min_val: The lower bound of the axis to set. Can also be a
            Specutils SpectralRegion
        :param max_val: The upper bound of the axis to set
        """
        if min_val:
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
        if max_val:
            # If user's value has a unit, convert it to the current axis' units
            if isinstance(max_val, u.Quantity):
                # Convert user's value to axis' units
                max_val = max_val.to(axis.unit).value
            # If auto, set to max_valimum wavelength value
            elif max_val == "auto":
                max_val = max(axis).value

            scale.max = float(max_val)

    def autoscale_x(self):
        """Sets the x-axis limits to the min/max of the reference data"""
        self.x_limits("auto", "auto")

    def autoscale_y(self):
        """Sets the y-axis limits to the min/max of the reference data"""
        self.y_limits("auto", "auto")

    def flip_x(self):
        """Flips the current limits of the x-axis"""
        scale = self.app.get_viewer("spectrum-viewer").scale_x
        self.x_limits(x_min=scale.max, x_max=scale.min)

    def flip_y(self):
        """Flips the current limits of the y-axis"""
        scale = self.app.get_viewer("spectrum-viewer").scale_y
        self.y_limits(y_min=scale.max, y_max=scale.min)

    def show(self):
        self.app
