import pathlib
from specutils import Spectrum1D

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

        """Loads a data file or Spectrum1D object into SpecViz

        :param data: Spectrum1D spectra, or path to compatible data file
        :param data_label: Name/identifier of data
        :param format: Spectrum1D data format to load
        """
        try:
            if pathlib.Path(data).is_file():
                data = Spectrum1D.read(data, format=format)
                self._app.add_data(data, data_label)
        except TypeError:
            self._app.add_data(data, data_label)
        self._app.add_data_to_viewer('spectrum-viewer', data_label)

    def get_spectra(self):
        """Returns the current data loaded into the main viewer"""
        return self._app.get_data_from_viewer('spectrum-viewer')
