import base64
import pathlib
import uuid
from astropy import units as u
from specutils import Spectrum1D, SpectrumCollection

import astropy.units as u
from specutils import Spectrum1D, SpectrumCollection, SpectralRegion

from jdaviz.core.helpers import ConfigHelper


class SpecViz(ConfigHelper):
    """SpecViz Helper class"""

    _default_configuration = 'specviz'

    def load_data(self, data, data_label=None, format=None):
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
            data_label = "specviz_data|" + str(base64.b85encode(uuid.uuid4().bytes), 'utf-8')
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
                raise TypeError("`SpectrumCollection` detected. Please "
                                "provide a `Spectrum1D`.")
            elif type(data) is not Spectrum1D:
                raise TypeError("Data is not a Spectrum1D object or compatible file")
        self.app.add_data(data, data_label)
        if show_in_viewer:
            self.app.add_data_to_viewer('spectrum-viewer', data_label)

    def get_spectra(self, data_label = None):
        """Returns the current data loaded into the main viewer"""
        return self.app.get_data_from_viewer('spectrum-viewer', data_label=data_label)

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
        regions = self.app.get_subsets_from_viewer('spectrum-viewer')

        spec_regs = {}

        for name, reg in regions.items():
            unit = reg.meta.get('spectral_axis_unit', u.Unit('Angstrom'))
            spec_reg = SpectralRegion.from_center(reg.center.x * unit,
                                                  reg.width * unit)

            spec_regs[name] = spec_reg

        return spec_regs
    def x_limits(self, x_min = None, x_max = None):
        scale = self.app.get_viewer('spectrum-viewer').scale_x
        if not x_min and not x_max:
            return scale
        
        if x_min:
            # If user's value has a unit, convert it to the current axis' units
            if isinstance(x_min, u.Quantity):
                # Get the current axis' units
                ref_index = self.app.get_viewer('spectrum-viewer').state.reference_data.label
                ref_unit = self.get_spectra(ref_index).spectral_axis.unit
                # Convert user's value to axis' units
                x_min = x_min.to(ref_unit).value
            # If auto, set to minimum wavelength value
            elif x_min == "auto":
                ref_index = self.app.get_viewer('spectrum-viewer').state.reference_data.label
                x_min = min(self.get_spectra()[ref_index].spectral_axis).value
            scale.min = float(x_min)
        if x_max:
            # If user's value has a unit, convert it to the current axis' units
            if isinstance(x_max, u.Quantity):
                # Get the current axis' units
                ref_index = self.app.get_viewer('spectrum-viewer').state.reference_data.label
                ref_unit = self.get_spectra(ref_index).spectral_axis.unit
                # Convert user's value to axis' units
                x_max = x_max.to(ref_unit).value
            # If auto, set to maximum wavelength value
            elif x_max == "auto":
                ref_index = self.app.get_viewer('spectrum-viewer').state.reference_data.label
                x_max = max(self.get_spectra()[ref_index].spectral_axis).value

            scale.max = float(x_max)
    
    def autoscale_x(self):
        self.x_limits('auto', 'auto')

    def flip_x(self):
        scale = self.app.get_viewer('spectrum-viewer').scale_x
        self.x_limits(x_min = scale.max, x_max = scale.min)

    def y_limits(self, y_min = None, y_max = None):
        scale = self.app.get_viewer('spectrum-viewer').scale_y
        if not y_min and not y_max:
            return scale
        if y_min:
            # If user's value has a unit, convert it to the current axis' units
            if isinstance(y_min, u.Quantity):
                # Get the current axis' units
                ref_index = self.app.get_viewer('spectrum-viewer').state.reference_data.label
                ref_unit = self.get_spectra(ref_index).unit
                # Convert user's value to axis' units
                y_min = y_min.to(ref_unit).value
            # If auto, set to minimum flux value
            elif y_min == "auto":
                ref_index = self.app.get_viewer('spectrum-viewer').state.reference_data.label
                y_min = min(self.get_spectra()[ref_index].flux).value
            scale.min = float(y_min)
        if y_max:
            # If user's value has a unit, convert it to the current axis' units
            if isinstance(y_max, u.Quantity):
                # Get the current axis' units
                ref_index = self.app.get_viewer('spectrum-viewer').state.reference_data.label
                ref_unit = self.get_spectra(ref_index).unit
                # Convert user's value to axis' units
                y_max = y_max.to(ref_unit).value
            # If auto, set to maximum flux value
            elif y_max == "auto":
                ref_index = self.app.get_viewer('spectrum-viewer').state.reference_data.label
                y_max = max(self.get_spectra()[ref_index].flux).value
            scale.max = float(y_max)

    def autoscale_y(self):
        self.y_limits('auto', 'auto')

    def flip_y(self):
        scale = self.app.get_viewer('spectrum-viewer').scale_y
        self.y_limits(y_min = scale.max, y_max = scale.min)

    def show(self):
        self.app
