from astrowidgets.core import ImageWidget
from ginga.misc.log import get_logger
from glue.core import Data
import ipywidgets as widgets

from jdaviz.core.registries import viewer_registry

__all__ = ['ImvizImageView']


class DummyModelID(widgets.Label):
    pass


class DummyState:
    def __init__(self):
        self.layers = []


@viewer_registry("imviz-image-viewer", label="Image 2D (Imviz)")
class ImvizImageView(ImageWidget):
    """Image widget for Imviz."""

    default_class = None
    state = DummyState()

    # session is a glue thing
    def __init__(self, session, *args, **kwargs):
        # logger needs special handling because using default logger of None
        # will crash Ginga internals.
        kwargs['logger'] = get_logger('imviz', log_stderr=True, log_file=None,
                                      level=30)
        super().__init__(*args, **kwargs)

    # More glue things

    def register_to_hub(self, *args, **kwargs):
        pass

    def add_data(self, data):
        if type(data) == Data:
            data = data.get_object()
        self.load_nddata(data)

    @property
    def toolbar_selection_tools(self):
        class Dummy(DummyModelID):
            def __init__(self):
                super().__init__()
                self.borderless = False

        return Dummy()

    @property
    def figure_widget(self):
        return self

    @property
    def layer_options(self):
        return DummyModelID()

    @property
    def viewer_options(self):
        return DummyModelID()

    def set_plot_axes(self, *args, **kwargs):
        pass

    def data(self, cls=None):
        return [layer_state.layer
                for layer_state in self.state.layers
                if hasattr(layer_state, 'layer') and
                isinstance(layer_state.layer, BaseData)]
