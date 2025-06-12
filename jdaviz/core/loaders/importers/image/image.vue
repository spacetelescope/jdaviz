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
    <v-row>
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
    </v-row>
  </v-contatiner>
</template>
<script setup lang="ts">
</script>
