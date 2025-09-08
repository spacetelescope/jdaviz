<template>
  <v-container>
    <plugin-select
      v-if="input_hdulist"
      :items="extension_items.map(i => i.label)"
      :selected.sync="extension_selected"
      :show_if_single_entry="true"
      label="Extension"
      api_hint="ldr.extension ="
      :api_hints_enabled="api_hints_enabled"
      hint="Extension to use from the FITS HDUList."
    />
    <plugin-auto-label
      :value.sync="data_label_value"
      :default="data_label_default"
      :auto.sync="data_label_auto"
      :invalid_msg="data_label_invalid_msg"
      label="Data Label"
      api_hint="ldr.importer.data_label ="
      :api_hints_enabled="api_hints_enabled"
      hint="Label to assign to the new data entry."
    ></plugin-auto-label>

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
      label="Viewer"
      api_hint='ldr.importer.viewer = '
      :api_hints_enabled="api_hints_enabled"
      :show_if_single_entry="true"
      hint="Select the viewer to use for the new data entry."
    ></plugin-viewer-create-new>

    <plugin-switch
      :value.sync="auto_extract"
      label="Extract 1D Spectrum"
      api_hint="ldr.importer.auto_extract ="
      :api_hints_enabled="api_hints_enabled"
      hint="Extract a 1D spectrum from the 2D data."
    ></plugin-switch>
    <div v-if="auto_extract">
      <plugin-auto-label
        :value.sync="ext_data_label_value"
        :default="ext_data_label_default"
        :auto.sync="ext_data_label_auto"
        :invalid_msg="ext_data_label_invalid_msg"
        label="Extracted 1D Spectrum Data Label"
        api_hint="ldr.importer.ext_data_label ="
        :api_hints_enabled="api_hints_enabled"
        hint="Label to assign to the auto-extracted 1D Spectrum."
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
        label="Viewer for Extracted Spectrum"
        api_hint='ldr.importer.ext_viewer = '
        :api_hints_enabled="api_hints_enabled"
        :show_if_single_entry="true"
        hint="Select the viewer to use for the new extracted 1D Spectrum data entry."
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
          'ldr.importer()'
          :
          'Import'
        }}
      </plugin-action-button>
    </v-row>
  </v-container>
</template>