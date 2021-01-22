from astrowidgets.core import ImageWidget
from ginga.misc.log import get_logger

from jdaviz.core.registries import viewer_registry

__all__ = ['ImvizImageView']


class DummyLayout:
    def __init__(self):
        self.height = ''
        self.width = ''


class DummyModelID:
    def __init__(self):
        self.model_id = '1234'
        self.layout = DummyLayout()


class ImvizImageWidget(ImageWidget):
    """Image widget for Imviz."""

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

    @property
    def toolbar_selection_tools(self):
        class Dummy(DummyModelID):
            def __init__(self):
                super().__init__()
                self.borderless = False

        return Dummy()

    @property
    def figure_widget(self):
        return DummyModelID()

    @property
    def layer_options(self):
        return DummyModelID()

    @property
    def viewer_options(self):
        return DummyModelID()


@viewer_registry("imviz-image-viewer", label="Image 2D (Imviz)")
class ImvizImageView(ImvizImageWidget):
    default_class = None
