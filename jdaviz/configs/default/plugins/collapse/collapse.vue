<template>
  <j-tray-plugin
    :config="config"
    plugin_key="Collapse"
    :api_hints_enabled.sync="api_hints_enabled"
    :description="docs_description"
    :link="docs_link || 'https://jdaviz.readthedocs.io/en/'+vdocs+'/'+config+'/plugins.html#collapse'"
    :popout_button="popout_button"
    :scroll_to.sync="scroll_to">

    <plugin-dataset-select
      :items="dataset_items"
      :selected.sync="dataset_selected"
      :show_if_single_entry="false"
      label="Data"
      api_hint="plg.dataset ="
      :api_hints_enabled="api_hints_enabled"
      hint="Select the data set to collapse."
    />

    <plugin-select
      :items="function_items.map(i => i.label)"
      :selected.sync="function_selected"
      label="Function"
      api_hint="plg.function ="
      :api_hints_enabled="api_hints_enabled"
      hint="Function to use in the collapse."
    />

    <plugin-subset-select
      :items="spectral_subset_items"
      :selected.sync="spectral_subset_selected"
      :has_subregions="spectral_subset_selected_has_subregions"
      :show_if_single_entry="true"
      has_subregions_warning="The selected selected subset has subregions, the entire range will be used, ignoring any gaps."
      label="Spectral region"
      api_hint="plg.spectral_subset ="
      :api_hints_enabled="api_hints_enabled"
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
      :action_spinner="spinner"
      add_results_api_hint='plg.add_results'
      action_api_hint='plg.collapse(add_data=True)'
      :api_hints_enabled="api_hints_enabled"
      @click:action="collapse"
    ></plugin-add-results>
  </j-tray-plugin>
</template>
