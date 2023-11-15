<template>
  <j-tray-plugin
    description='Extract a spectrum from a spectral cube.'
    :link="docs_link || 'https://jdaviz.readthedocs.io/en/'+vdocs+'/'+config+'/plugins.html#spectral-extraction'"
    :popout_button="popout_button"
    :disabled_msg="disabled_msg">

    <v-row>
      <v-select
        :menu-props="{ left: true }"
        attach
        :items="function_items.map(i => i.label)"
        v-model="function_selected"
        label="Function"
        hint="Function for reducing dimensions of spectral cube."
        persistent-hint
      ></v-select>
    </v-row>

    <plugin-subset-select 
      :items="spatial_subset_items"
      :selected.sync="spatial_subset_selected"
      :show_if_single_entry="true"
      label="Spatial region"
      hint="Select a spatial region to extract its spectrum."
    />

    <plugin-add-results
      :label.sync="results_label"
      :label_default="results_label_default"
      :label_auto.sync="results_label_auto"
      :label_invalid_msg="results_label_invalid_msg"
      :label_overwrite="results_label_overwrite"
      label_hint="Label for the extracted spectrum"
      :add_to_viewer_items="add_to_viewer_items"
      :add_to_viewer_selected.sync="add_to_viewer_selected"
      action_label="Extract"
      action_tooltip="Run spectral extraction with error and mask propagation"
      :action_spinner="spinner"
      @click:action="spectral_extraction"
    ></plugin-add-results>

  </j-tray-plugin>
</template>
