from astrowidgets.glupyter import ImageWidget
from glue.core import BaseData

from jdaviz.core.registries import viewer_registry

__all__ = ['ImvizImageView']


@viewer_registry("imviz-image-viewer", label="Image 2D (Imviz)")
class ImvizImageView(ImageWidget):
    """Image widget for Imviz."""

    default_class = None

    # session is a glue thing
    def __init__(self, session, *args, **kwargs):

        super().__init__(*args, **kwargs)
        self._viewer._session = session

    # More glue things

    def register_to_hub(self, *args, **kwargs):
        self._viewer.register_to_hub(*args, **kwargs)

    def add_data(self, data):
        self._viewer.add_data(data)
        self._link_image_to_cb()

    def remove_data(self, data):
        self._viewer.remove_data(data)
        self.viewer.interaction = None

    @property
    def toolbar_selection_tools(self):
        return self._viewer.toolbar_selection_tools

    @property
    def figure_widget(self):
        return self

    @property
    def layer_options(self):
        return self._viewer.layer_options

    @property
    def viewer_options(self):
        return self._viewer.viewer_options

    @property
    def state(self):
        return self._viewer.state

    def set_plot_axes(self):
        self.viewer.axes[1].tick_format = None
        self.viewer.axes[0].tick_format = None

        self.viewer.axes[1].label = "y: pixels"
        self.viewer.axes[0].label = "x: pixels"

        # Make it so y axis label is not covering tick numbers.
        self.viewer.axes[1].label_offset = "-50"

    def data(self, cls=None):
        return [layer_state.layer
                for layer_state in self._viewer.state.layers
                if hasattr(layer_state, 'layer') and
                isinstance(layer_state.layer, BaseData)]
