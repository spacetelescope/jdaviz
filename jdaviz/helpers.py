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
    def __init__(self):
        super().__init__(configuration="specviz")

    def load_data(self, data, data_label, format=None):
        try:
            if pathlib.Path(data).is_file():
                data = Spectrum1D.read(data, format=format)
                self._app.add_data(data, data_label)
        except TypeError:
            self._app.add_data(data, data_label)
        self._app.add_data_to_viewer('spectrum-viewer', data_label)

    def get_spectra(self):
        return self._app.get_data_from_viewer('spectrum-viewer')
