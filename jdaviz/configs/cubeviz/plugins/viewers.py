from glue.core import BaseData
from glue_jupyter.bqplot.image import BqplotImageView

from jdaviz.core.registries import viewer_registry

__all__ = ['CubeVizImageView']


@viewer_registry("cubeviz-image-viewer", label="Image 2D (CubeViz)")
class CubeVizImageView(BqplotImageView):
    default_class = None

    def set_plot_axes(self):
        self.figure.axes[1].tick_format = None
        self.figure.axes[0].tick_format = None

        self.figure.axes[1].label = "y: pixels"
        self.figure.axes[0].label = "x: pixels"

        # Make it so y axis label is not covering tick numbers.
        self.figure.axes[1].label_offset = "-50"

    def data(self, cls=None):
        return [layer_state.layer  # .get_object(cls=cls or self.default_class)
                for layer_state in self.state.layers
                if hasattr(layer_state, 'layer') and
                isinstance(layer_state.layer, BaseData)]
