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
      hint="Select a parent dataset to associate the new data with."
    ></plugin-dataset-select>
    <v-row>
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
    </v-row>
  </v-container>
</template>
<script setup lang="ts">
</script>
