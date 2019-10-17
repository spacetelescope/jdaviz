from traitlets import Unicode, List, Int

from jdaviz.core.registries import trays, viewers
from jdaviz.core.template_mixin import TemplateMixin
from glue.core.message import DataCollectionAddMessage

from ipyvuetify import Card

from jdaviz.core.events import AddViewerMessage, DataSelectedMessage, NewViewerMessage


@trays("g-data-collection-list", label="Data Collection", icon='cloud_download')
class DataCollectionListComponent(TemplateMixin):
    item = Int(1).tag(sync=True)
    items = List([]).tag(sync=True)
    viewers = List([]).tag(sync=True)

    template = Unicode("""
    <v-list>
      <v-subheader>Data</v-subheader>
    
      <v-list-item-group v-model="item" color="primary">
        <v-list-item 
            v-for="(item, i) in items" 
            :key="i" 
            @click="data_selected(i)">
          <v-list-item-action>
            <v-menu offset-y 
                @click.native.stop>
              <template 
                v-slot:activator="{ on }">
                <v-btn icon v-on="on">
                  <v-icon>menu</v-icon>
                </v-btn>
              </template>
              <v-list>
                <v-list-item 
                    v-for="(viewer, index) in viewers" 
                    :key="index" 
                    @click="">
                  <v-list-item-title
                    @click="create_viewer(viewer.name, index)">
                        {{ viewer.label }}
                  </v-list-item-title>
                </v-list-item>
              </v-list>
            </v-menu>
          </v-list-item-action>
    
          <v-list-item-content>
            <v-list-item-title 
                v-text="item.text">
            </v-list-item-title>
          </v-list-item-content>
        </v-list-item>
      </v-list-item-group>
    </v-list>
    """).tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Load in the references to the viewer registry. Because traitlets
        #  can't serialize the actual viewer class reference, create a list of
        #  dicts containing just the viewer name and label.
        self.viewers = [{'name': k, 'label': v['label']}
                        for k, v in viewers.members.items()]

        # Subscribe to the event fired when data is added to the application-
        # level data collection object
        self.hub.subscribe(self, DataCollectionAddMessage,
                           handler=self._on_data_added)

    def vue_data_selected(self, index):
        # Broadcast an event containing the index in the data collection of
        #  the data selected in the data list.
        data_selected_message = DataSelectedMessage(index, sender=self)
        self.hub.broadcast(data_selected_message)

    def vue_create_viewer(self, name, index):
        viewer_cls = viewers.members[name]['cls']
        data = self.data_collection[index]

        new_viewer_msg = NewViewerMessage(viewer_cls, data, sender=self)
        self.hub.broadcast(new_viewer_msg)

    def _on_data_added(self, msg):
        self.items = self.items + [{'text': msg.data.label,
                                    'icon': 'mdi-clock'}]


@trays("g-viewer-options", label="Viewer Options", icon='save')
class ViewerOptionsComponent(TemplateMixin):
    template = Unicode("""
    <g-holder></g-holder>
    """).tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.components = {'g-holder': Card(flat=True)}

        self.hub.subscribe(self, AddViewerMessage, handler=self._on_viewer_added)

    def _on_viewer_added(self, msg):
        self.components.get('g-holder').children = [msg.viewer.viewer_options]


@trays("g-layer-options", label="Layer Options", icon='save')
class LayerOptionsComponent(TemplateMixin):
    template = Unicode("""
    <g-holder></g-holder>
    """).tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.components = {'g-holder': Card(flat=True)}

        self.hub.subscribe(self, AddViewerMessage, handler=self._on_viewer_added)

    def _on_viewer_added(self, msg):
        self.components.get('g-holder').children = [msg.viewer.layer_options]
