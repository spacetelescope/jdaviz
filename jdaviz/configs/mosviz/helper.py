from jdaviz.core.helpers import ConfigHelper
from specutils import Spectrum1D, SpectrumCollection
from glue.core.data import Data
from jdaviz.core.events import NewViewerMessage
from jdaviz.core.registries import viewer_registry
from jdaviz.core.events import ConfigurationLoadedMessage



def _compose_labels():
    pass


class MosViz(ConfigHelper):
    """MosViz Helper class"""
    _default_configuration = 'mosviz'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # self._on_configuration_loaded()

    def _on_configuration_loaded(self):
        data = Data(label="MOS Table")
        # data.add_component(comp_data, label=label)
        self.app.data_collection.append(data)

        # Set the table viewer data to render
        # viewer = self.app.get_viewer("table-viewer")
        # viewer.add_data(data)

        # viewer_cls = viewer_registry.members["mosviz-table-viewer"]['cls']
        #
        # new_viewer_message = NewViewerMessage(
        #     viewer_cls, data=data, sender=self)
        #
        # self.app.hub.broadcast(new_viewer_message)

    def load_1d_spectra(self, data_obj, data_labels=None):
        if data_labels is None or len(data_obj) != len(data_labels):
            data_labels = [f"1D Spectrum {i}" for i in range(len(data_obj))]

        if hasattr(data_obj, '__len__'):
            for i in range(len(data_obj)):
                self.app.data_collection[data_labels[i]] = data_obj[i]

        # Add data to the mos viz table object
        if 'MOS Table' not in self.app.data_collection:
            data = Data(label="MOS Table")
            self.app.data_collection.append(data)

            mos_table = self.app.data_collection['MOS Table']
            mos_table.add_component(data_labels, "1D Spectra")

            viewer = self.app.get_viewer("table-viewer")
            viewer.add_data(data)
        else:
            mos_table = self.app.data_collection['MOS Table']
            mos_table.add_component(data_labels, "1D Spectra")

    def load_2d_spectra(self, data_obj, data_labels=None):
        if data_labels is None or len(data_obj) != len(data_labels):
            data_labels = [f"2D Spectrum {i}" for i in range(len(data_obj))]

        if hasattr(data_obj, '__len__'):
            for i in range(len(data_obj)):
                self.app.data_collection[data_labels[i]] = data_obj[i]

        # Add data to the mos viz table object
        if 'MOS Table' not in self.app.data_collection:
            data = Data(label="MOS Table")
            self.app.data_collection.append(data)

            mos_table = self.app.data_collection['MOS Table']
            mos_table.add_component(data_labels, "2D Spectra")

            viewer = self.app.get_viewer("table-viewer")
            viewer.add_data(data)
        else:
            mos_table = self.app.data_collection['MOS Table']
            mos_table.add_component(data_labels, "2D Spectra")

    def load_images(self, data_obj, data_labels=None):
        if data_labels is None or len(data_obj) != len(data_labels):
            data_labels = [f"Image {i}" for i in range(len(data_obj))]

        if hasattr(data_obj, '__len__'):
            for i in range(len(data_obj)):
                self.app.data_collection[data_labels[i]] = data_obj[i]

        # Add data to the mos viz table object
        if 'MOS Table' not in self.app.data_collection:
            data = Data(label="MOS Table")
            self.app.data_collection.append(data)

            mos_table = self.app.data_collection['MOS Table']
            mos_table.add_component(data_labels, "Images")

            viewer = self.app.get_viewer("table-viewer")
            viewer.add_data(data)
        else:
            mos_table = self.app.data_collection['MOS Table']
            mos_table.add_component(data_labels, "Images")

