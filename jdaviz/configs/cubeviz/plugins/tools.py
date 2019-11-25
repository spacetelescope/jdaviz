from ipyvuetify import VuetifyTemplate
from traitlets import Unicode, List, Int, Bool, Dict, Any

from jdaviz.core.registries import tools
from jdaviz.core.template_mixin import TemplateMixin
from jdaviz.core.events import (LoadDataMessage, DataSelectedMessage,
                                AddViewerMessage)

from glue.core.edit_subset_mode import (OrMode, AndNotMode, AndMode, XorMode,
                                        ReplaceMode)
from glue.core.message import EditSubsetMessage


@tools('cv-import-data')
class CubevizImportDataButton(TemplateMixin):
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
        for path in ["/Users/nearl/data/cubeviz/MaNGA/manga-7495-12704-LOGCUBE.fits"]:
            load_data_message = LoadDataMessage(path, sender=self)
            self.hub.broadcast(load_data_message)

        self.dialog = False
