<template>
  <v-container>
    <div v-if="!disable_dropdown && exposures_items.length > 0">
      <plugin-select
        :items="exposures_items.map(i => i.label)"
        :selected.sync="exposures_selected"
        :show_if_single_entry="true"
        :multiselect="exposures_multiselect"
        :search="true"
        label="Exposure"
        api_hint="ldr.importer.exposures ="
        :api_hints_enabled="api_hints_enabled"
        hint="Exposures to select from."
      ></plugin-select>
    </div>

    <div style="height: 8px;"></div>

    <div v-if="!disable_dropdown">
      <plugin-select
        :items="spectra_items.map(i => i.label)"
        :selected.sync="spectra_selected"
        :show_if_single_entry="true"
        :multiselect="spectra_multiselect"
        :search="true"
        label="Source IDs"
        api_hint="ldr.importer.spectra ="
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
