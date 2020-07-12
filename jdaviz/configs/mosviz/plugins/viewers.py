from glue.core import BaseData
from glue_jupyter.bqplot.image import BqplotImageView
from glue_jupyter.bqplot.profile import BqplotProfileView
from specutils import Spectrum1D
from glue_jupyter.table import TableViewer

from jdaviz.core.registries import viewer_registry

__all__ = ['MOSVizProfileView', 'MOSVizImageView']


@viewer_registry("mosviz-profile-viewer", label="Profile 1D (MOSViz)")
class MOSVizProfileView(BqplotProfileView):
    default_class = Spectrum1D

    def data(self, cls=None):
        return [layer_state.layer.get_object(cls=cls or self.default_class)
                for layer_state in self.state.layers
                if hasattr(layer_state, 'layer') and
                isinstance(layer_state.layer, BaseData)]


@viewer_registry("mosviz-image-viewer", label="Image 2D (MOSViz)")
class MOSVizImageView(BqplotImageView):

    default_class = None

    def data(self, cls=None):
        return [layer_state.layer #.get_object(cls=cls or self.default_class)
                for layer_state in self.state.layers
                if hasattr(layer_state, 'layer') and
                isinstance(layer_state.layer, BaseData)]


DEFAULT_COLUMNS = ['ID', 'Image', '1D Spectrum', '2D Spectrum', 'RA', 'DEC']


@viewer_registry("mosviz-table-viewer", label="Table (MOSViz)")
class MOSVizTableViewer(TableViewer):
    def __init__(self, session, *args, **kwargs):
        super().__init__(session, *args, **kwargs)
