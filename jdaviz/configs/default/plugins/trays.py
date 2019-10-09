from traitlets import Unicode, List, Int

from jdaviz.core.registries import trays
from jdaviz.core.template_mixin import TemplateMixin
from glue.core.message import DataCollectionAddMessage


@trays("g-data-collection-list")
class DataCollectionListComponent(TemplateMixin):
    item = Int(1).tag(sync=True)
    items = List([]).tag(sync=True)

    template = Unicode("""
    <v-list>
      <v-subheader>Data</v-subheader>
      <v-list-item-group v-model="item" color="primary">
        <v-list-item
                v-for="(item, i) in items"
                :key="i"
        >
          <v-list-item-icon>
            <v-icon v-text="item.icon"></v-icon>
          </v-list-item-icon>
          <v-list-item-content>
            <v-list-item-title v-text="item.text"></v-list-item-title>
          </v-list-item-content>
        </v-list-item>
      </v-list-item-group>
    </v-list>
    """).tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.hub.subscribe(self, DataCollectionAddMessage, handler=self._on_data_added)

    def _on_data_added(self, msg):
        self.items = self.items + [{'text': msg.data.label, 'icon': 'mdi-clock'}]

