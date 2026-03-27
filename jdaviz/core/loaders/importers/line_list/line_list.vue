<template>
  <v-container>
    <plugin-auto-label
      :value.sync="line_list_label_value"
      :default="line_list_label_default"
      :auto.sync="line_list_label_auto"
      :invalid_msg="line_list_label_invalid_msg"
      label="Line List Name"
      api_hint="ldr.importer.line_list_label ="
      :api_hints_enabled="api_hints_enabled"
      hint="Name to assign to the imported line list."
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
