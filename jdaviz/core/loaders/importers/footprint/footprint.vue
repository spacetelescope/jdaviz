<template>
  <v-container>
    <plugin-auto-label
      :value.sync="footprint_label_value"
      :default="footprint_label_default"
      :auto.sync="footprint_label_auto"
      :invalid_msg="footprint_label_invalid_msg"
      label="Footprint Label"
      api_hint="ldr.importer.footprint_label ="
      :api_hints_enabled="api_hints_enabled"
      hint="Label to assign to the new footprint overlay."
    ></plugin-auto-label>

    <loader-import-button
      :spinner="import_spinner"
      :disabled_msg="import_disabled_msg"
      :api_hints_enabled="api_hints_enabled"
      api_hint="ldr.load()"
      @click="import_clicked">
    </loader-import-button>
  </v-container>
</template>