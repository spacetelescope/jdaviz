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

    <v-row justify="end">
      <plugin-action-button
        :spinner="import_spinner"
        :disabled="import_disabled"
        :results_isolated_to_plugin="false"
        :api_hints_enabled="api_hints_enabled"
        @click="import_clicked">
        {{ api_hints_enabled ?
          'ldr.load()'
          :
          'Import'
        }}
      </plugin-action-button>
    </v-row>
  </v-container>
</template>