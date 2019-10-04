import os

from glue.core.message import (DataCollectionAddMessage,)
from traitlets import (Unicode, List, Bool, Int)
from ipywidgets import IntSlider, Text
import ipyvuetify as v

from ..core.template_mixin import TemplateMixin

with open(os.path.join(os.path.dirname(__file__), "interact_drawer.vue")) as f:
    TEMPLATE = f.read()


class InteractDrawer(TemplateMixin):
    """
    Application navigation drawer containing the lists of data and subsets
    currently in the glue collection.
    """
    drawer = Bool(True).tag(sync=True)
    mini = Bool(False).tag(sync=True)
    data_items = List([]).tag(sync=True)
    subset_items = List([]).tag(sync=True)
    selected = Int(-1).tag(sync=True)

    template = Unicode(TEMPLATE).tag(sync=True)

    def __init__(self, *args, **kwargs):
        self._viewer_options = v.CardTitle()
        self._layer_options = v.CardTitle()

        super().__init__(*args, components={'b-viewer-options': self._viewer_options,
                                            'b-layer-options': self._layer_options},
            **kwargs)
