<template>
    <v-container>
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
      <plugin-switch
        :value.sync="auto_extract"
        label="Extract 1D Spectrum"
        api_hint="ldr.importer.auto_extract ="
        :api_hints_enabled="api_hints_enabled"
        hint="Extract a 1D spectrum from the 2D data."
      ></plugin-switch>
      <v-row v-if="auto_extract">
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
      </v-row>
    </v-contatiner>
  </template>