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
@trays("g-data-collection-list", label="Data Collection", icon='mdi-database')
class DataCollectionTreeComponent(TemplateMixin):
    item = Int(1).tag(sync=True, allow_none=True)
    items = List([]).tag(sync=True)
    viewers = List([]).tag(sync=True)

    template = Unicode("""
    <v-card
      class="mx-auto"
      outline
      tile
    >
      <v-toolbar
        dense
        flat
        fixed
      >
        <v-app-bar-nav-icon></v-app-bar-nav-icon>

        <v-spacer></v-spacer>

        <v-btn icon>
          <v-icon>mdi-magnify</v-icon>
        </v-btn>
      </v-toolbar>
      <v-divider
      ></v-divider>
      <v-container style="max-height: 100vh; overflow-y: auto" >
        <v-row dense>
          <v-col cols="12"
          >
            <v-treeview :items="items"
                        hoverable
                        activatable
                        dense
                        open-on-click
            ></v-treeview>
          </v-col>
        </v-row>
      </v-container>
    </v-card>
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
        self.items = self.items + [{'name': msg.data.label,
                                    'icon': 'mdi-clock'}]


@trays('g-viewer-options', label="Viewer Options", icon='mdi-view-dashboard')
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


@trays('g-layer-options', label="Layer Options", icon='mdi-chart-scatter-plot')
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
