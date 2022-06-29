<template>
  <j-tray-plugin
    description='Create a 2D image from a data cube.'
    :link="'https://jdaviz.readthedocs.io/en/'+vdocs+'/'+config+'/plugins.html#moment-maps'"
    :popout_button="popout_button">

    <plugin-dataset-select
      :items="dataset_items"
      :selected.sync="dataset_selected"
      :show_if_single_entry="false"
      label="Data"
      hint="Select the data set."
    />

    <plugin-subset-select 
      :items="spectral_subset_items"
      :selected.sync="spectral_subset_selected"
      :has_subregions="spectral_subset_selected_has_subregions"
      :show_if_single_entry="true"
      has_subregions_warning="The selected selected subset has subregions, the entire range will be used, ignoring any gaps."
      label="Spectral region"
      hint="Spectral region to compute the moment map."
    />

    <v-row>
      <v-text-field
        ref="n_moment"
        type="number"
        label="Moment"
        v-model.number="n_moment"
        hint="The desired moment."
        persistent-hint
        :rules="[() => !!n_moment || 'This field is required']"
      ></v-text-field>
    </v-row>

    <plugin-add-results
      :label.sync="results_label"
      :label_default="results_label_default"
      :label_auto.sync="results_label_auto"
      :label_invalid_msg="results_label_invalid_msg"
      :label_overwrite="results_label_overwrite"
      label_hint="Label for the collapsed cube"
      :add_to_viewer_items="add_to_viewer_items"
      :add_to_viewer_selected.sync="add_to_viewer_selected"
      action_label="Calculate"
      action_tooltip="Calculate moment map"
      @click:action="calculate_moment"
    ></plugin-add-results>

    <div v-if="moment_available">
      <j-plugin-section-header>Results</j-plugin-section-header>
      <v-row>
          <v-text-field
           v-model="filename"
           label="Filename"
           hint="Export the latest calculated moment map"
           :rules="[() => !!filename || 'This field is required']"
           persistent-hint>
          </v-text-field>
      </v-row>
      <v-row justify="end">
        <j-tooltip tipid='plugin-moment-save-fits'>
          <v-btn color="primary" text @click="save_as_fits">Save as FITS</v-btn>
        </j-tooltip>
      </v-row>
    </div>
  </j-tray-plugin>
</template>
