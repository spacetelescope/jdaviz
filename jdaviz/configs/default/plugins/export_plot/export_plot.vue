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
      <v-list>
       <v-list-item>
        <v-btn
         color="primary"
         @click="() => save_figure('png')"
        >
         Export to PNG
        </v-btn>
       </v-list-item>
       <v-list-item>
        <v-btn
         color="primary"
         @click="() => save_figure('svg')"
        >
         Export to SVG
        </v-btn>
       </v-list-item>
      </v-list>

      <v-row v-if="config=='cubeviz'" no-gutters>
        <v-expansion-panels popout>
          <v-expansion-panel>
            <v-expansion-panel-header v-slot="{ open }">
              <span style="padding: 6px">Export to Video</span>
            </v-expansion-panel-header>
            <v-expansion-panel-content>
              <v-row class="row-no-outside-padding row-min-bottom-padding">
                <v-col>
                  <v-text-field
                    v-model="i_start"
                    class="mt-0 pt-0"
                    type="number"
                    label="Start"
                    hint="Start Slice"
                  ></v-text-field>
                </v-col>
                <v-col>
                  <v-text-field
                    v-model="i_end"
                    class="mt-0 pt-0"
                    type="number"
                    label="End"
                    hint="End Slice"
                  ></v-text-field>
                </v-col>
              </v-row>
              <v-row class="row-no-outside-padding row-min-bottom-padding">
                <v-col>
                  <v-text-field
                    v-model="movie_filename"
                    class="mt-0 pt-0"
                    label="Filename"
                    hint="Movie filename"
                  ></v-text-field>
                </v-col>
              </v-row>
              <v-row>
                <v-btn
                 color="primary"
                 @click="() => save_movie('mp4')"
                >
                 Export to MP4
                </v-btn>
              </v-row>
            </v-expansion-panel-content>
          </v-expansion-panel>
        </v-expansion-panels>
      </v-row>
    </div>

  </j-tray-plugin>
</template>
