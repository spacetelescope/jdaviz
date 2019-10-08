from traitlets import Unicode, List, Int

from jdaviz.core.registries import trays
from jdaviz.core.template_mixin import TemplateMixin


@trays("g-data-collection-list")
class DataCollectionListComponent(TemplateMixin):
    item = Int(1).tag(sync=True)
    items = List([
        { 'text': 'single_g235h-f170lp_x1d.fits', 'icon': 'mdi-clock' },
        { 'text': 'single_g235h-f170lp_x1d.fits', 'icon': 'mdi-account' },
        { 'text': 'single_g235h-f170lp_x1d.fits', 'icon': 'mdi-flag' },
    ]).tag(sync=True)

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

