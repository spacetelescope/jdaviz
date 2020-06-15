import pathlib
import uuid
from specutils import Spectrum1D, SpectrumCollection

from .app import Application

class ConfigHelper():
    """The Base Helper Class
    Provides shared abstracted helper methods to the user
    """
    def __init__(self, configuration=None):
        self._app = Application(configuration=configuration)


class SpecViz(ConfigHelper):
    """SpecViz Helper class"""

    def __init__(self):
        """Instantiates base helper with specviz configuration"""
        super().__init__(configuration="specviz")

    def load_data(self, data, data_label='', format=None):
        """Loads a data file or Spectrum1D object into SpecViz

        :param data: Spectrum1D spectra, or path to compatible data file
        :param data_label: Name/identifier of data
        :param format: Spectrum1D data format to load
        """
        # If no data label is assigned, give it a unique identifier
        if not data_label:
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
                raise TypeError("SpectrumCollection detected. Please provide a Spectrum1D")
            elif type(data) is not Spectrum1D:
                raise TypeError("Data is not a Spectrum1D object or compatible file")
        self._app.add_data(data, data_label)
        self._app.add_data_to_viewer('spectrum-viewer', data_label)

    def get_spectra(self):
        """Returns the current data loaded into the main viewer"""
        return self._app.get_data_from_viewer('spectrum-viewer')
