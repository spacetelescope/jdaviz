<template>
  <v-container>
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