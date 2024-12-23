<template>
  <j-tray-plugin
    :description="docs_description"
    :link="docs_link || 'https://jdaviz.readthedocs.io/en/'+vdocs+'/'+config+'/plugins.html#cubeviz-sonify-data'"
    :uses_active_status="uses_active_status"
    @plugin-ping="plugin_ping($event)"
    :keep_active.sync="keep_active"
    :popout_button="popout_button"
    :scroll_to.sync="scroll_to"
    :disabled_msg="disabled_msg">

    <j-plugin-section-header>Sonify Cube</j-plugin-section-header>
    <v-alert v-if="!has_strauss" type="warning" style="margin-left: -12px; margin-right: -12px">
      To use Sonify Data, install strauss and restart Jdaviz. You can do this by running pip install strauss
      in the command line and then launching Jdaviz.
    </v-alert>

    <plugin-subset-select
      :items="spectral_subset_items"
      :selected.sync="spectral_subset_selected"
      :show_if_single_entry="true"
      label="Spectral range"
      api_hint="plg.spectral_subset ="
      :api_hints_enabled="api_hints_enabled"
      hint="Select spectral region that defines the wavelength range."
    />

    <v-row>
      <v-expansion-panels accordion>
        <v-expansion-panel>
          <v-expansion-panel-header v-slot="{ open }">
            <span style="padding: 6px">Advanced Sound Options</span>
          </v-expansion-panel-header>
          <v-expansion-panel-content class="plugin-expansion-panel-content">
            <v-row>
              <v-text-field
                ref="sample_rate"
                type="number"
                label="Sample Rate"
                v-model.number="sample_rate"
                hint="The desired sample rate."
                persistent-hint
              ></v-text-field>
            </v-row>
            <v-row>
              <v-text-field
                ref="buffer_size"
                type="number"
                label="Buffer Size"
                v-model.number="buffer_size"
                hint="The desired buffer size."
                persistent-hint
              ></v-text-field>
            </v-row>
            <v-row>
              <v-text-field
                ref="audfrqmin"
                type="number"
                label="Minimum Audio Frequency"
                v-model.number="audfrqmin"
                hint="The minimum audio frequency used to represent the spectra (Hz)"
                persistent-hint
              ></v-text-field>
            </v-row>
            <v-row>
              <v-text-field
                ref="audfrqmax"
                type="number"
                label="Maximum Audio Frequency"
                v-model.number="audfrqmax"
                hint="The maximum audio frequency used to represent the spectra (Hz)"
                persistent-hint
              ></v-text-field>
            </v-row>
            <v-row>
              <v-text-field
                ref="assidx"
                type="number"
                label="Audio Spectrum Scaling Index"
                v-model.number="assidx"
                hint="The desired audio spectrum scaling index, typically > 1."
                persistent-hint
              ></v-text-field>
            </v-row>
            <v-row>
              <v-text-field
                ref="ssvidx"
                type="number"
                label="Spectrum-Spectrum Volume Index"
                v-model.number="ssvidx"
                hint="The desired spectrum-spectrum volume index, typically [0,1]."
                persistent-hint
              ></v-text-field>
            </v-row>
            <v-row>
              <v-text-field
                ref="pccut"
                type="number"
                label="Flux Percentile Cut"
                v-model.number="pccut"
                hint="The minimum flux percentile to be heard."
                persistent-hint
              ></v-text-field>
            </v-row>
            <v-row>
               <v-switch
                 v-model="eln"
                 label="Equal Loudness Equalisation"
                 hint="Whether to equalise for uniform perceived loudness"
                 persistent-hint
                ></v-switch>
            </v-row>
          </v-expansion-panel-content>
        </v-expansion-panel>
      </v-expansion-panels>
    </v-row>

    <v-row>
      <plugin-action-button
        :spinner="spinner"
        @click="sonify_cube"
      >
        Sonify data
      </plugin-action-button>
      <plugin-action-button v-if="!stream_active"
        @click="start_stop_stream"
      >
        Start stream
      </plugin-action-button>
      <plugin-action-button v-if="stream_active"
        @click="start_stop_stream"
      >
        Stop stream
      </plugin-action-button>
    </v-row>
    <v-row>
      <v-select
        :menu-props="{ left: true }"
        attach
        :items="sound_devices_items"
        v-model="sound_devices_selected"
        label="Sound device"
        hint="Device which sound will be output from. Must be selected BEFORE cube is sonified."
        persistent-hint
        ></v-select>
    </v-row>
    <v-row>
        Volume
        <glue-throttled-slider label="Volume" wait="300" max="100" step="1" :value.sync="volume" hide-details class="no-hint" />
    </v-row>
 </j-tray-plugin>
</template>