<template>
  <v-container>
    <div v-if="!disable_dropdown">
        <plugin-select
          :items="spectra_items.map(i => i.label)"
          :selected.sync="spectra_selected"
          :show_if_single_entry="true"
          :multiselect="spectra_multiselect"
          label="Source IDs"
          api_hint="ldr.spectra.selected ="
          :api_hints_enabled="api_hints_enabled"
          hint="Source IDs to select from the list of spectra."
        ></plugin-select>
    </div>

    <div style="height: 16px;"></div>

    <v-row>
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
    </v-row>
  </v-container>
</template>
