import os

from glue.core.message import (DataCollectionAddMessage,)
from glue_jupyter.baldr.core.events import NewProfile1DMessage
from traitlets import (Unicode, List, Bool, Int)
from ipywidgets import IntSlider, Text
import ipyvuetify as v

from glue_jupyter.baldr.core.template_mixin import TemplateMixin

with open(os.path.join(os.path.dirname(__file__), "navigation_drawer.vue")) as f:
    TEMPLATE = f.read()


class NavigationDrawer(TemplateMixin):
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

        self.hub.subscribe(self, DataCollectionAddMessage,
                           handler=self._data_added)
        self.hub.subscribe(self, NewProfile1DMessage,
                           handler=self._profile_added)

    def _data_added(self, message):
        self.data_items = self.data_items + [{'title': "{}".format(message.data.label),
                                    'icon': 'dashboard', 'selected': False}]

    def _profile_added(self, msg):
        self._viewer_options.children = [msg.figure.viewer_options]
        self._layer_options.children = [msg.figure.layer_options]

    def vue_data_selected(self, index):
        new_data_item = self.data_items[index] if index > 0 else None
        old_data_item = self.data_items[self.selected] if self.selected > 0 else None

        if self.selected == index:
            if old_data_item is not None:
                self._set_data_item_selected(old_data_item, index, False)
            self.selected = -1
        else:
            if index > 0 and self.selected > 0:
                self._set_data_item_selected(old_data_item, index, False)

            self.selected = index

            if index > 0:
                print("Setting {} to active.".format(index))
                self._set_data_item_selected(new_data_item, index, True)

    def _set_data_item_selected(self, item, index, state):
        data_items = [x for x in self.data_items]
        self.data_items[index]['selected'] = state
        print(self.data_items[index])
        # self.data_items = data_items
