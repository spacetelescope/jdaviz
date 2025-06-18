<template>
  <v-row>
    <plugin-auto-label
      :value.sync="subset_label_value"
      :default="subset_label_default"
      :auto.sync="subset_label_auto"
      :invalid_msg="subset_label_invalid_msg"
      label="Subset Label"
      api_hint="ldr.importer.subset_label ="
      :api_hints_enabled="api_hints_enabled"
      hint="Label to assign to the new subset."
    ></plugin-auto-label>
  </v-row>
</template>