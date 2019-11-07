import ipyvuetify as v
from glue.core.message import DataCollectionAddMessage
from glue_jupyter.utils import validate_data_argument
from traitlets import Unicode, List, Int

from jdaviz.core.events import DataSelectedMessage, NewViewerMessage, \
    ViewerSelectedMessage
from jdaviz.core.registries import trays, viewers
from jdaviz.core.template_mixin import TemplateMixin


# TODO: right now, the list items don't elide (the right button will get
#  pushed out of the right side). There are solutions in vuetify for this
#  but they need to be implemented.
@trays("g-data-collection-list", label="Data Collection", icon='cloud_download')
class DataCollectionListComponent(TemplateMixin):
    item = Int(1).tag(sync=True)
    items = List([]).tag(sync=True)
    viewers = List([]).tag(sync=True)

    template = Unicode("""
    <v-list dense nav>
      <v-list-item-group v-model="item" color="primary">
        <v-list-item 
            v-for="(item, i) in items" 
            :key="i" 
            @click="data_selected(i)">
    
          <v-list-item-content>
            <v-list-item-title 
                v-text="item.text">
            </v-list-item-title>
          </v-list-item-content>
          
          <v-list-item-action>
            <v-menu offset-y>
              <template 
                v-slot:activator="{ on }">
                <v-btn small icon v-on="on" @click.stop="">
                  <v-icon>menu</v-icon>
                </v-btn>
              </template>
              <v-list>
                <v-list-item 
                    v-for="(viewer, index) in viewers" 
                    :key="index" 
                    @click="create_viewer({name: viewer.name, index: i})">
                  <v-list-item-title>
                        {{ viewer.label }}
                  </v-list-item-title>
                </v-list-item>
              </v-list>
            </v-menu>
          </v-list-item-action>
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

    def vue_create_viewer(self, data):
        name = data.get('name')
        index = data.get('index')

        viewer_cls = viewers.members[name]['cls']

        data = validate_data_argument(self.data_collection,
                                      self.data_collection[index])

        new_viewer_message = NewViewerMessage(
            viewer_cls, data=data, sender=self)

        self.hub.broadcast(new_viewer_message)

    def _on_data_added(self, msg):
        self.items = self.items + [{'text': msg.data.label,
                                    'icon': 'mdi-clock'}]


@trays('g-viewer-options', label="Viewer Options", icon='save')
class ViewerOptionsTray(TemplateMixin):
    template = Unicode("""
    <g-viewer-options-holder></g-viewer-options-holder>
    """).tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.components = {
            'g-viewer-options-holder': v.Sheet()}

        self.hub.subscribe(self, ViewerSelectedMessage,
                           handler=self._on_viewer_selected)

    def _on_viewer_selected(self, msg):
        self.components.get('g-viewer-options-holder').children = [msg.viewer.viewer_options]


@trays('g-layer-options', label="Layer Options", icon='save')
class LayerOptionsTray(TemplateMixin):
    template = Unicode("""
    <g-layer-options-holder></g-layer-options-holder>
    """).tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.components = {
            'g-layer-options-holder': v.Sheet()}

        self.hub.subscribe(self, ViewerSelectedMessage,
                           handler=self._on_viewer_selected)

    def _on_viewer_selected(self, msg):
        self.components.get('g-layer-options-holder').children = [msg.viewer.layer_options]
