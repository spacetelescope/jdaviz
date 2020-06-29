import pathlib
import uuid

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
        if data_label is None:
            data_label = "specviz_data|" + uuid.uuid4().hex

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
        self.app.add_data_to_viewer('spectrum-viewer', data_label)

    def get_spectra(self):
        """Returns the current data loaded into the main viewer"""
        return self.app.get_data_from_viewer('spectrum-viewer')

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
