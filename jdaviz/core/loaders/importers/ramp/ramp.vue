<template>
  <v-container>
    <plugin-select
      v-if="integration_items.length > 0"
      :items="integration_items.map(i => i.label)"
      :selected.sync="integration_selected"
      :show_if_single_entry="false"
      label="Integration"
      api_hint="ldr.importer.integration ="
      :api_hints_enabled="api_hints_enabled"
      hint="Select the integration to use from the ramp data."
    ></plugin-select>

    <j-plugin-section-header>Ramp Cube</j-plugin-section-header>
    <v-row>
      <j-docs-link>Display the cumulative samples up-the-ramp at a given group number g<sub>i</sub>, as one image per group.</j-docs-link>
    </v-row>


    <plugin-auto-label
      :value.sync="data_label_value"
      :default="data_label_default"
      :auto.sync="data_label_auto"
      :invalid_msg="data_label_invalid_msg"
      label="Data Label"
      api_hint="ldr.importer.data_label ="
      :api_hints_enabled="api_hints_enabled"
      hint="Label to assign to the new data entry for the ramp cube."
    >
    </plugin-auto-label>

    <plugin-viewer-create-new
      :items="viewer_items"
      :selected.sync="viewer_selected"
      :create_new_items="viewer_create_new_items"
      :create_new_selected.sync="viewer_create_new_selected"
      :new_label_value.sync="viewer_label_value"
      :new_label_default="viewer_label_default"
      :new_label_auto.sync="viewer_label_auto"
      :new_label_invalid_msg="viewer_label_invalid_msg"
      :multiselect="viewer_multiselect"
      :show_multiselect_toggle="false"
      label="Viewer for Ramp Cube"
      api_hint='ldr.importer.viewer = '
      :api_hints_enabled="api_hints_enabled"
      :show_if_single_entry="true"
      hint="Select the viewer to use for the imported ramp cube."
    ></plugin-viewer-create-new>

    <j-plugin-section-header>Difference Cube</j-plugin-section-header>
    <v-row>
      <j-docs-link>Display the difference image between group numbers g<sub>i</sub>-g<sub>i-1</sub>, e.g., only the counts accumulated between the previous group and the current group.</j-docs-link>
    </v-row>

    <plugin-auto-label
      :value.sync="diff_data_label_value"
      :default="diff_data_label_default"
      :auto.sync="diff_data_label_auto"
      :invalid_msg="diff_data_label_invalid_msg"
      label="Data Label for the Difference Cube"
      api_hint="ldr.importer.diff_data_label ="
      :api_hints_enabled="api_hints_enabled"
      hint="Label to assign to the new difference cube data entry."
    ></plugin-auto-label>

    <plugin-viewer-create-new
      :items="diff_viewer_items"
      :selected.sync="diff_viewer_selected"
      :create_new_items="diff_viewer_create_new_items"
      :create_new_selected.sync="diff_viewer_create_new_selected"
      :new_label_value.sync="diff_viewer_label_value"
      :new_label_default="diff_viewer_label_default"
      :new_label_auto.sync="diff_viewer_label_auto"
      :new_label_invalid_msg="diff_viewer_label_invalid_msg"
      :multiselect="diff_viewer_multiselect"
      :show_multiselect_toggle="false"
      label="Viewer for Difference Cube"
      api_hint='ldr.importer.diff_viewer = '
      :api_hints_enabled="api_hints_enabled"
      :show_if_single_entry="true"
      hint="Select the viewer to use for the imported difference cube."
    ></plugin-viewer-create-new>

    <j-plugin-section-header>Ramp Integration</j-plugin-section-header>
    <v-row>
      <j-docs-link>Display the cumulative counts per group as a function of group number; for a single pixel, or for a statistic (mean, median, min, max, sum) of the counts for groups of pixels.</j-docs-link>
    </v-row>

    <plugin-switch
      :value.sync="auto_extract"
      label="Extract Ramp Integration"
      api_hint="ldr.importer.auto_extract ="
      :api_hints_enabled="api_hints_enabled"
      hint="Extract a the integrated ramp from the entire cube (use the Ramp Extraction Plugin after importing to extract for a particular spatial subset)."
    ></plugin-switch>
    <div v-if="auto_extract">
      <plugin-select
        :items="function_items.map(i => i.label)"
        :selected.sync="function_selected"
        label="Function"
        api_hint="ldr.importer.function ="
        :api_hints_enabled="api_hints_enabled"
        hint="Select the function to apply to the extracted ramp integration."
      ></plugin-select>

      <plugin-auto-label
        :value.sync="ext_data_label_value"
        :default="ext_data_label_default"
        :auto.sync="ext_data_label_auto"
        :invalid_msg="ext_data_label_invalid_msg"
        label="Data Label for the Ramp Integration"
        api_hint="ldr.importer.ext_data_label ="
        :api_hints_enabled="api_hints_enabled"
        hint="Label to assign to the new ramp integration data entry."
      ></plugin-auto-label>

      <plugin-viewer-create-new
        :items="ext_viewer_items"
        :selected.sync="ext_viewer_selected"
        :create_new_items="ext_viewer_create_new_items"
        :create_new_selected.sync="ext_viewer_create_new_selected"
        :new_label_value.sync="ext_viewer_label_value"
        :new_label_default="ext_viewer_label_default"
        :new_label_auto.sync="ext_viewer_label_auto"
        :new_label_invalid_msg="ext_viewer_label_invalid_msg"
        :multiselect="ext_viewer_multiselect"
        :show_multiselect_toggle="false"
        label="Viewer for Extracted Ramp Integration"
        api_hint='ldr.importer.ext_viewer = '
        :api_hints_enabled="api_hints_enabled"
        :show_if_single_entry="true"
        hint="Select the viewer to use for the imported extracted ramp integration."
      ></plugin-viewer-create-new>
    </div>

    <v-row justify="end">
      <plugin-action-button
        :spinner="import_spinner"
        :disabled="import_disabled"
        :results_isolated_to_plugin="false"
        :api_hints_enabled="api_hints_enabled"
        @click="import_clicked">
        {{ api_hints_enabled ?
          'ldr.load()'
          :
          'Import'
        }}
      </plugin-action-button>
    </v-row>
  </v-container>
</template>