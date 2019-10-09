from ipyvuetify import VuetifyTemplate
from traitlets import Unicode, List, Int, Bool, Dict, Any

from jdaviz.core.registries import tools
from jdaviz.core.template_mixin import TemplateMixin
from jdaviz.core.events import LoadDataMessage

__all__ = ['OpenSessionButton', 'SaveSessionButton', 'ImportDataButton', 'ExportDataButton']


@tools('spacer')
class Spacer(VuetifyTemplate):
    template = Unicode("""
            <div class="flex-grow-1"></div>
            """).tag(sync=True)


@tools('vertical-divider')
class VerticalDivider(VuetifyTemplate):
    template = Unicode("""
            <v-divider vertical></v-divider>
            """).tag(sync=True)


@tools('g-open-session')
class OpenSessionButton(TemplateMixin):
    template = Unicode("""
    <v-btn text class="mx-1">
        <v-icon left>folder</v-icon>
        Open Session
    </v-btn>
    """).tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


@tools('g-save-session')
class SaveSessionButton(TemplateMixin):
    template = Unicode("""
    <v-btn text class="mx-1">
        <v-icon left>save</v-icon>
        Save Session
    </v-btn>
    """).tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


@tools('g-import-data')
class ImportDataButton(TemplateMixin):
    valid = Bool(True).tag(sync=True)
    dialog = Bool(False).tag(sync=True)
    file_paths = Any(None).tag(sync=True)

    template = Unicode("""
    <div class="text-center">
        <v-dialog
          v-model="dialog"
          width="500"
          persistent
        >
          <template v-slot:activator="{ on }">
            <v-btn
              dark
              v-on="on"
              text
              class="mx-1"
            >
              <v-icon left>cloud_download</v-icon>
              Import Data
            </v-btn>
          </template>
    
            <v-form v-model="valid">
              <v-card>
                <v-card-title
                  class="headline grey lighten-2"
                  primary-title
                >
                  Import Data
                </v-card-title>
                
                <v-card-text>
                    <v-file-input 
                        show-size 
                        counter 
                        label="File input" 
                        v-model="file_paths"
                    ></v-file-input>
                </v-card-text>
                <v-divider></v-divider>
        
                <v-card-actions>
                  <div class="flex-grow-1"></div>
                  <v-btn
                    color="primary"
                    text
                    @click="dialog = false"
                  >
                    Cancel
                  </v-btn>
                  <v-btn
                    color="primary"
                    text
                    @click="load_data"
                  >
                    Import
                  </v-btn>
                </v-card-actions>
              </v-card>
            </v-form>
        </v-dialog>
      </div>
    """).tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def vue_load_data(self, *args, **kwargs):
        # TODO: hack because of current incompatibility with ipywidget types
        #  and vuetify templates.
        for path in ["/Users/nearl/data/single_g235h-f170lp_x1d.fits"]:
            load_data_message = LoadDataMessage(path, sender=self)
            self.hub.broadcast(load_data_message)

        self.dialog = False


@tools('g-export-data')
class ExportDataButton(TemplateMixin):
    template = Unicode("""
    <v-btn text class="mx-1">
        <v-icon left>save_alt</v-icon>
        Export Data
    </v-btn>
    """).tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


@tools('g-active-subset')
class ActiveSubsetDropdown(TemplateMixin):
    subsets = List([]).tag(sync=True)

    template = Unicode("""
    <v-overflow-btn
        :items="subsets"
        label="Current subset"
        target="#dropdown-example"
        hide-details
        class="pa-0"
        overflow
        width="500px"
    ></v-overflow-btn>
    """).tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


@tools('g-selection-state')
class SelectStateButtonGroup(TemplateMixin):
    toggle_one = Int(0).tag(sync=True)
    template = Unicode("""
    <v-btn-toggle light v-model="toggle_one" mandatory class="my-2">
      <v-btn text>
        <v-icon>cloud_download</v-icon>
      </v-btn>
      <v-btn text>
        <v-icon>cloud_download</v-icon>
      </v-btn>
      <v-btn text>
        <v-icon>cloud_download</v-icon>
      </v-btn>
      <v-btn text>
        <v-icon>cloud_download</v-icon>
      </v-btn>
    </v-btn-toggle>
    """).tag(sync=True)
