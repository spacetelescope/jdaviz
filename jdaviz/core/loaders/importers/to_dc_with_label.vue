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
  </v-contatiner>
</template>