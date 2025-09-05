<template>
  <v-container>
    <plugin-select
      v-if="!disable_dropdown"
      :items="sources_items.map(i => i.label)"
      :selected.sync="sources_selected"
      :show_if_single_entry="true"
      :multiselect="sources_multiselect"
      :search="true"
      label="Source IDs"
      api_hint="ldr.importer.sources ="
      :api_hints_enabled="api_hints_enabled"
      hint="Source IDs to select from the list of sources."
    ></plugin-select>

<!-- TODO: Re-enable this when viewer logic is corrected for
           spectrum list with both SB and flux units
    <plugin-switch
      v-if="input_in_sb"
      :value.sync="convert_to_flux_density"
      label="Convert to flux density units"
      api_hint="ldr.importer.convert_to_flux_density = "
      :api_hints_enabled="api_hints_enabled"
      hint="Whether to convert any input surface brightness units to flux density."
    ></plugin-switch>
-->
    <div style="height: 16px;"></div>

    <plugin-auto-label
      :value.sync="data_label_value"
      :default="data_label_default"
      :auto.sync="data_label_auto"
      :invalid_msg="data_label_invalid_msg"
      label="Data Label Prefix"
      api_hint="ldr.importer.data_label ="
      :api_hints_enabled="api_hints_enabled"
      hint="Prefix label to assign to the new data entries."
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
