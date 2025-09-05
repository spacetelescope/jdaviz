<template>
  <v-container>
    <plugin-select
      :items="extension_items.map(i => i.label)"
      :selected.sync="extension_selected"
      :show_if_single_entry="true"
      :multiselect="extension_multiselect"
      label="Extension"
      api_hint="ldr.extension ="
      :api_hints_enabled="api_hints_enabled"
      hint="Extension to use from the FITS HDUList."
    ></plugin-select>
    <plugin-dataset-select
      :items="parent_items"
      :selected.sync="parent_selected"
      :show_if_single_entry="false"
      :multiselect="false"
      label="Parent Dataset"
      api_hint="ldr.importer.parent ="
      :api_hints_enabled="api_hints_enabled"
      hint="Advanced: manually select a dataset to associate as the parent of the new data entry, 'Auto' will automatically associate non-science extensions with the science extension."
    ></plugin-dataset-select>
    <plugin-auto-label
      :value.sync="data_label_value"
      :default="data_label_default"
      :auto.sync="data_label_auto"
      :invalid_msg="data_label_invalid_msg"
      label="Data Label"
      api_hint="ldr.importer.data_label ="
      :api_hints_enabled="api_hints_enabled"
      :hint="data_label_is_prefix ? 'Prefix to assign to the new data entry.' : 'Label to assign to the new data entry.'"
    ></plugin-auto-label>
    <v-row>
      <plugin-switch
        :value.sync="gwcs_to_fits_sip"
        label="Approximate GWCS with FITS SIP"
        api_hint="ldr.importer.gwcs_to_fits_sip = "
        :api_hints_enabled="api_hints_enabled"
        hint="If GWCS exists, try to convert into FITS SIP for better performance aligning images (typical precision <0.1 pixels)."
      />
    </v-row>

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
