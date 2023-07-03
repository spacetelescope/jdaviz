<template>
  <j-tray-plugin
    description='Export viewer plot as an image.'
    :link="'https://jdaviz.readthedocs.io/en/'+vdocs+'/'+config+'/plugins.html#export-plot'"
    :popout_button="popout_button">

    <plugin-viewer-select
      :items="viewer_items"
      :selected.sync="viewer_selected"
      label="Viewer"
      hint="Select the viewer to export."
    />

    <div v-if="viewer_selected">
      <v-row justify="end" class="row-min-bottom-padding">
        <v-btn
         text
         color="primary"
         @click="() => save_figure('png')"
         :disabled="movie_recording"
        >
         Export to PNG
        </v-btn>
      </v-row>
      <v-row justify="end">
        <v-btn
         text
         color="primary"
         @click="() => save_figure('svg')"
         :disabled="movie_recording"
        >
         Export to SVG
        </v-btn>
      </v-row>

      <v-row v-if="config==='cubeviz' && viewer_selected!=='spectrum-viewer'">
        <v-expansion-panels accordion>
          <v-expansion-panel>
            <v-expansion-panel-header v-slot="{ open }">
              <span style="padding: 6px">Export to Video</span>
            </v-expansion-panel-header>
            <v-expansion-panel-content>
              <v-row v-if="movie_msg!==''">
                <span class="v-messages v-messages__message text--secondary" style="color: red !important">
                    {{ movie_msg }}
                </span>
              </v-row>
              <v-row v-if="movie_msg===''" class="row-no-outside-padding row-min-bottom-padding">
                <v-col>
                  <v-text-field
                    v-model.number="i_start"
                    class="mt-0 pt-0"
                    type="number"
                    :rules="[() => i_start>=0 || 'Must be at least zero.']"
                    label="Start"
                    hint="Start Slice"
                    persistent-hint
                  ></v-text-field>
                </v-col>
                <v-col>
                  <v-text-field
                    v-model.number="i_end"
                    class="mt-0 pt-0"
                    type="number"
                    :rules="[() => i_end>i_start || 'Must be larger than Start Slice.']"
                    label="End"
                    hint="End Slice"
                     persistent-hint
                  ></v-text-field>
                </v-col>
              </v-row>
              <v-row v-if="movie_msg===''" class="row-no-outside-padding row-min-bottom-padding">
                <v-col>
                  <v-text-field
                    v-model.number="movie_fps"
                    class="mt-0 pt-0"
                    type="number"
                    :rules="[() => movie_fps>0 || 'Must be positive.']"
                    label="FPS"
                    hint="Frame rate"
                     persistent-hint
                  ></v-text-field>
                </v-col>
              </v-row>
              <v-row v-if="movie_msg===''" class="row-no-outside-padding row-min-bottom-padding">
                <v-col>
                  <v-text-field
                    v-model="movie_filename"
                    class="mt-0 pt-0"
                    :rules="[() => movie_filename!=='' || 'Must provide filename.']"
                    label="Filename"
                    hint="Movie filename"
                     persistent-hint
                  ></v-text-field>
                </v-col>
              </v-row>
              <v-row v-if="movie_msg===''" justify='end'>
                <v-tooltip top v-if="movie_recording">
                  <template v-slot:activator="{ on, attrs }">
                    <v-btn
                     color="primary"
                     icon
                     @click="interrupt_recording"
                     v-bind="attrs"
                     v-on="on"
                     :disabled="!movie_recording">
                      <v-icon>stop</v-icon>
                    </v-btn>
                  </template>
                  <span>Interrupt recording and delete movie file</span>
                </v-tooltip>

                <v-tooltip top>
                  <template v-slot:activator="{ on, attrs }">
                    <v-btn
                     text
                     color="primary"
                     @click="() => save_movie('mp4')"
                     v-bind="attrs"
                     v-on="on"
                     :disabled="movie_recording"
                    >
                     Export to MP4
                    </v-btn>
                  </template>
                  <span>Start movie recording</span>
                </v-tooltip>
              </v-row>
            </v-expansion-panel-content>
          </v-expansion-panel>
        </v-expansion-panels>
      </v-row>
    </div>

  </j-tray-plugin>
</template>
