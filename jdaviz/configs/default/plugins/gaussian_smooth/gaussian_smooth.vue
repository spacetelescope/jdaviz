<template>
  <j-tray-plugin
    :description="config==='cubeviz' ? 'Smooth data cube spatially or spectrally with a Gaussian kernel.' : 'Smooth data with a Gaussian kernel.'"
    :link="'https://jdaviz.readthedocs.io/en/'+vdocs+'/'+config+'/plugins.html#gaussian-smooth'"
    :popout_button="popout_button">

      <!-- for mosviz, the entries change on row change, so we want to always show the dropdown
           to make sure that is clear -->
      <plugin-dataset-select
        :items="dataset_items"
        :selected.sync="dataset_selected"
        :show_if_single_entry="config=='mosviz'"
        label="Data"
        hint="Select the data to be smoothed."
      />

      <v-row v-if="show_modes">
        <v-select
          :menu-props="{ left: true }"
          attach
          :items="mode_items.map(i => i.label)"
          v-model="mode_selected"
          label="Mode"
          hint="Smooth data spectrally or spatially."
          persistent-hint
        ></v-select>
      </v-row>

      <v-row>
        <v-text-field
          ref="stddev"
          type="number"
          label="Standard deviation"
          v-model.number="stddev"
          type="number"
          hint="The stddev of the kernel, in pixels."
          persistent-hint
          :rules="[() => !!stddev || 'This field is required',
                   () => stddev > 0 || 'Kernel must be greater than zero']"
        ></v-text-field>
      </v-row>

      <plugin-add-results
        :label.sync="results_label"
        :label_default="results_label_default"
        :label_auto.sync="results_label_auto"
        :label_invalid_msg="results_label_invalid_msg"
        :label_overwrite="results_label_overwrite"
        label_hint="Label for the smoothed data"
        :add_to_viewer_items="add_to_viewer_items"
        :add_to_viewer_selected.sync="add_to_viewer_selected"
        action_label="Smooth"
        action_tooltip="Smooth data"
        @click:action="apply"
      ></plugin-add-results>
    </j-tray-plugin>
</template>
