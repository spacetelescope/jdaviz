from ipyvuetify import VuetifyTemplate
from traitlets import Unicode, List, Int, Bool, Dict, Any

from jdaviz.core.registries import tools
from jdaviz.core.template_mixin import TemplateMixin
from jdaviz.core.events import LoadDataMessage, DataSelectedMessage

from glue.core.edit_subset_mode import OrMode, AndNotMode, AndMode, XorMode, ReplaceMode
from glue.core.message import EditSubsetMessage

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
    <v-btn min-width="0" dense tile text class="px-2 mx-1">
        <v-icon>folder</v-icon>
    </v-btn>
    """).tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


@tools('g-save-session')
class SaveSessionButton(TemplateMixin):
    template = Unicode("""
    <v-btn min-width="0" dense tile text class="px-2 mx-1">
        <v-icon>save</v-icon>
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
              min-width="0"
              dense
              tile
              text
              class="px-2 mx-1"
            >
              <v-icon>cloud_download</v-icon>
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
            print("HERE")
            load_data_message = LoadDataMessage(path, sender=self)
            self.hub.broadcast(load_data_message)

        self.dialog = False


@tools('g-export-data')
class ExportDataButton(TemplateMixin):
    template = Unicode("""
    <v-btn min-width="0" dense tile text class="px-2 mx-1">
        <v-icon>save_alt</v-icon>
    </v-btn>
    """).tag(sync=True)

    css = Unicode("""
    .v-btn {
      min-width: 0;
    }
    """).tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


@tools('g-subset-select')
class SubsetSelectTool(TemplateMixin):
    subsets = List(['one', 'two']).tag(sync=True)

    template = Unicode("""
    <v-overflow-btn
        :items="subsets"
        label="Selected subsets"
        target="#dropdown-example"
        hide-details
        overflow
        min_width="300px"
        multiple
        height=46
        dense
        chips
        deletable-chips
    ></v-overflow-btn>
    """).tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


SUBSET_MODES = {
    'replace': ReplaceMode,
    'add': OrMode,
    'and': AndMode,
    'xor': XorMode,
    'remove': AndNotMode
}


@tools('g-subset-mode')
class SubsetModeTool(TemplateMixin):
    index = Int(0).tag(sync=True)
    template = Unicode("""
    <v-btn-toggle v-model="index" mandatory group dense>
      <v-btn>
        <v-icon>mdi-checkbox-blank-circle</v-icon>
      </v-btn>
      <v-btn>
        <v-icon>mdi-set-all</v-icon>
      </v-btn>
      <v-btn>
        <v-icon>mdi-set-center</v-icon>
      </v-btn>
      <v-btn>
        <v-icon>mdi-set-left-right</v-icon>
      </v-btn>
      <v-btn>
        <v-icon>mdi-set-center-right</v-icon>
      </v-btn>
    </v-btn-toggle>
    """).tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Observe messages that change the subset mode state
        self.session.hub.subscribe(
            self, EditSubsetMessage, handler=self._on_subset_edited)
        self.observe(self._subset_mode_selected, 'index')

    def _subset_mode_selected(self, index):
        self.session.edit_subset_mode.mode = list(SUBSET_MODES.values())[index]

    def _on_subset_edited(self, msg):
        if self.session.edit_subset_mode.mode != msg.mode:
            self.session.edit_subset_mode.mode = msg.mode

        self.index = list(SUBSET_MODES.values()).index(msg.mode)
