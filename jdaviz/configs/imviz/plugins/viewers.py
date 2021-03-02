from glue.core import BaseData
from glue_jupyter.bqplot.image import BqplotImageView

from jdaviz.core.registries import viewer_registry

__all__ = ['ImVizImageView']


@viewer_registry("imviz-image-viewer", label="Image 2D (ImViz)")
class ImVizImageView(BqplotImageView):

    tools = ['bqplot:panzoom', 'bqplot:rectangle', 'bqplot:circle', 'bqplot:coords']

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
