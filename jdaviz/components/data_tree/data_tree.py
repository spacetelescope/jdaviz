import os

from glue.core.message import DataCollectionAddMessage
from glue_jupyter.utils import validate_data_argument
from traitlets import Unicode, List, Int

from jdaviz.core.events import DataSelectedMessage, NewViewerMessage
from jdaviz.core.registries import trays, viewers
from jdaviz.core.template_mixin import TemplateMixin

__all__ = ['DataTree']

with open(os.path.join(os.path.dirname(__file__), "data_tree.vue")) as f:
    TEMPLATE = f.read()


# TODO: right now, the list items don't elide (the right button will get
#  pushed out of the right side). There are solutions in vuetify for this
#  but they need to be implemented.
# @trays("g-data-tree", label="Data", icon='mdi-database')
class DataTree(TemplateMixin):
    items = List([]).tag(sync=True)
    selected = List([]).tag(sync=True)
    template = Unicode(TEMPLATE).tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Subscribe to the event fired when data is added to the application-
        # level data collection object
        self.hub.subscribe(self, DataCollectionAddMessage,
                           handler=self._on_data_added)

    def _on_data_added(self, msg):
        self.items = self.items + [
            {
                'id': len(self.items),
                'name': msg.data.label,
                'children': [
                    # {'id': 2, 'name': 'Calendar : app'},
                    # {'id': 3, 'name': 'Chrome : app'},
                    # {'id': 4, 'name': 'Webstorm : app'},
                ],
            }
        ]

    def vue_on_activated(self, event):
        print(event)
