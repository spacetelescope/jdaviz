<template>
    <j-tray-plugin>
      <v-row>
        <j-docs-link :link="'https://jdaviz.readthedocs.io/en/'+vdocs+'/'+config+'/plugins.html#gaussian-smooth'">Smooth your data in xy or wavelength with a Gaussian kernel</j-docs-link>
      </v-row>

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
          :items="smooth_modes"
          v-model="selected_mode"
          label="Smoothing Type"
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
          :rules="[() => !!stddev || 'This field is required', () => stddev > 0 || 'Kernel must be greater than zero']"
        ></v-text-field>
      </v-row>

      <plugin-add-results
        :label.sync="results_label"
        label_hint="Label for the smoothed data"
        :label_changed_by_user.sync="results_label_changed_by_user"
        :add_to_viewer_items="add_to_viewer_items"
        :add_to_viewer_selected.sync="add_to_viewer_selected"
      ></plugin-add-results>

      <v-row justify="end">
        <j-tooltip tipid='plugin-gaussian-apply'>
          <v-btn :disabled="stddev <= 0 || dataset_selected == ''"
            color="accent" text 
            @click="apply"
          >Apply</v-btn>
        </j-tooltip>
      </v-row>
    </j-tray-plugin>
</template>
