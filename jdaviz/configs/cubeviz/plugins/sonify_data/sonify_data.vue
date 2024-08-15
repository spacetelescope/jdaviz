<template>
  <j-tray-plugin
    :description="docs_description || 'Create a 2D image from a data cube.'"
    :link="docs_link || 'https://jdaviz.readthedocs.io/en/'+vdocs+'/'+config+'/plugins.html#moment-maps'"
    :uses_active_status="uses_active_status"
    @plugin-ping="plugin_ping($event)"
    :keep_active.sync="keep_active"
    :popout_button="popout_button"
    :scroll_to.sync="scroll_to">

    <j-plugin-section-header>Cube</j-plugin-section-header>
    <v-row>
      <j-docs-link>Choose the input cube and spectral subset.</j-docs-link>
    </v-row>

    <plugin-dataset-select
      :items="dataset_items"
      :selected.sync="dataset_selected"
      :show_if_single_entry="false"
      label="Data"
      hint="Select the data set."
    />

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
        ref="wavemin"
        type="number"
        label="Minimum Wavelength"
        v-model.number="wavemin"
        hint="The desired minimum wavelength."
        persistent-hint
      ></v-text-field>
    </v-row>
    <v-row>
      <v-text-field
        ref="wavemax"
        type="number"
        label="Maximum Wavelength"
        v-model.number="wavemax"
        hint="The desired maximum wavelength."
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
    <v-row>
        <plugin-action-button
        @click="sonify_cube"
      >
        Sonify data
      </plugin-action-button>
    </v-row>
 </j-tray-plugin>
</template>