from glue.core import BaseData
from glue_jupyter.bqplot.image import BqplotImageView
from glue_jupyter.bqplot.profile import BqplotProfileView
from specutils import Spectrum1D

from jdaviz.core.registries import viewer_registry

__all__ = ['CubeVizImageView']

@viewer_registry("cubeviz-image-viewer", label="Image 2D (CubeViz)")
class CubeVizImageView(BqplotImageView):
    default_class = None

    def data(self, cls=None):
        return [layer_state.layer #.get_object(cls=cls or self.default_class)
                for layer_state in self.state.layers
                if hasattr(layer_state, 'layer') and
                isinstance(layer_state.layer, BaseData)]
