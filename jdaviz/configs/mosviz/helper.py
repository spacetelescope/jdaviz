from jdaviz.core.helpers import ConfigHelper
from specutils import Spectrum1D, SpectrumCollection
from glue.core.data import Data
from jdaviz.core.events import NewViewerMessage
from jdaviz.core.registries import viewer_registry



def _compose_labels():
    pass


class MosViz(ConfigHelper):
    """MosViz Helper class"""
    _default_configuration = 'mosviz'

    def _create_table(self, comp_data, label):
        data = Data(label="MOS Table")
        data.add_component(comp_data, label=label)
        self.app.data_collection.append(data)

        viewer_cls = viewer_registry.members["mosviz-table-viewer"]['cls']

        new_viewer_message = NewViewerMessage(
            viewer_cls, data=data, sender=self)

        self.app.hub.broadcast(new_viewer_message)

    def load_1d_spectra(self, data_obj, data_labels=None):
        pass

    def load_2d_spectra(self, data_obj):
        pass

    def load_images(self, data_obj):
        pass

