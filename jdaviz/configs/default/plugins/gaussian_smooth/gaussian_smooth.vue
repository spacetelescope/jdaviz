<template>
  <j-tray-plugin
    :config="config"
    plugin_key="Gaussian Smooth"
    :api_hints_enabled.sync="api_hints_enabled"
    :description="docs_description"
    :link="docs_link || 'https://jdaviz.readthedocs.io/en/'+vdocs+'/'+config+'/plugins.html#gaussian-smooth'"
    :popout_button="popout_button"
    :scroll_to.sync="scroll_to">

      <plugin-select
        v-if="show_modes"
        :items="mode_items.map(i => i.label)"
        :selected.sync="mode_selected"
        label="Mode"
        api_hint="plg.mode ="
        :api_hints_enabled="api_hints_enabled"
        hint="Smooth data spectrally or spatially."
      />

      <!-- for mosviz, the entries change on row change
           for cubeviz, the entries change when toggling "cube fit"
           so let's always show the dropdown for those cases to make the selection clear -->
      <plugin-dataset-select
        :items="dataset_items"
        :selected.sync="dataset_selected"
        :show_if_single_entry="['mosviz', 'cubeviz'].indexOf(config) !== -1"
        label="Data"
        api_hint='plg.dataset ='
        :api_hints_enabled="api_hints_enabled"
        hint="Select the data to be smoothed."
      />

      <v-row>
        <v-text-field
          ref="stddev"
          :label="api_hints_enabled ? 'plg.stddev =' : 'Standard deviation'"
          :class="api_hints_enabled ? 'api-hint' : null"
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
        :action_spinner="spinner"
        add_results_api_hint='plg.add_results'
        action_api_hint='plg.smooth(add_data=True)'
        :api_hints_enabled="api_hints_enabled"
        @click:action="apply"
      ></plugin-add-results>
    </j-tray-plugin>
</template>
