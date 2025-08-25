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

    <plugin-viewer-select
      :items="viewer_items"
      :selected.sync="viewer_selected"
      :multiselect="false"
      :show_multiselect_toggle="false"
      label="Viewer"
      api_hint='ldr.importer.viewer = '
      :api_hints_enabled="api_hints_enabled"
      :show_if_single_entry="true"
      hint="Select the viewer to use for the new data entry."
    ></plugin-viewer-select>

    <v-row v-if="viewer_selected === 'Create New...'">
      <plugin-auto-label
        :value.sync="viewer_label_value"
        :default="viewer_label_default"
        :auto.sync="viewer_label_auto"
        :invalid_msg="viewer_label_invalid_msg"
        label="Viewer Label"
        api_hint="ldr.importer.viewer_label ="
        :api_hints_enabled="api_hints_enabled"
        hint="Label to assign to the new viewer."
      ></plugin-auto-label>
    </v-row>
  </v-container>
</template>