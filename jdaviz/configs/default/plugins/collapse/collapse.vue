<template>
  <j-tray-plugin
    description='Collapse a spectral cube along one axis.'
    :link="'https://jdaviz.readthedocs.io/en/'+vdocs+'/'+config+'/plugins.html#collapse'"
    :popout_button="popout_button">

    <plugin-dataset-select
      :items="dataset_items"
      :selected.sync="dataset_selected"
      :show_if_single_entry="false"
      label="Data"
      hint="Select the data set to collapse."
    />

    <v-row>
      <v-select
        :menu-props="{ left: true }"
        attach
        :items="function_items.map(i => i.label)"
        v-model="function_selected"
        label="Function"
        hint="Function to use in the collapse."
        persistent-hint
      ></v-select>
    </v-row>

    <plugin-subset-select 
      :items="spectral_subset_items"
      :selected.sync="spectral_subset_selected"
      :has_subregions="spectral_subset_selected_has_subregions"
      :show_if_single_entry="true"
      has_subregions_warning="The selected selected subset has subregions, the entire range will be used, ignoring any gaps."
      label="Spectral region"
      hint="Select spectral region to apply the collapse."
    />

    <plugin-add-results
      :label.sync="results_label"
      :label_default="results_label_default"
      :label_auto.sync="results_label_auto"
      :label_invalid_msg="results_label_invalid_msg"
      :label_overwrite="results_label_overwrite"
      label_hint="Label for the collapsed cube"
      :add_to_viewer_items="add_to_viewer_items"
      :add_to_viewer_selected.sync="add_to_viewer_selected"
      action_label="Collapse"
      action_tooltip="Collapse data"
      @click:action="collapse"
    ></plugin-add-results>

  </j-tray-plugin>
</template>
