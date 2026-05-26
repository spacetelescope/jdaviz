<template>
  <v-container>
    <plugin-auto-label
      v-model:value="data_label_value"
      :default="data_label_default"
      v-model:auto="data_label_auto"
      :invalid_msg="data_label_invalid_msg"
      label="Data Label"
      api_hint="ldr.importer.data_label ="
      :api_hints_enabled="api_hints_enabled"
      hint="Label to assign to the new data entry."
    >
    </plugin-auto-label>

    <plugin-viewer-create-new
      :items="viewer_items"
      v-model:selected="viewer_selected"
      :create_new_items="viewer_create_new_items"
      v-model:create_new_selected="viewer_create_new_selected"
      v-model:new_label_value="viewer_label_value"
      :new_label_default="viewer_label_default"
      v-model:new_label_auto="viewer_label_auto"
      :new_label_invalid_msg="viewer_label_invalid_msg"
      :multiselect="viewer_multiselect"
      :show_multiselect_toggle="false"
      label="Viewer"
      api_hint='ldr.importer.viewer = '
      :api_hints_enabled="api_hints_enabled"
      :show_if_single_entry="true"
      hint="Select the viewer to use for the new data entry."
    ></plugin-viewer-create-new>

    <loader-import-button
      :spinner="import_spinner"
      :disabled_msg="import_disabled_msg"
      :api_hints_enabled="api_hints_enabled"
      api_hint="ldr.load()"
      :data_label_overwrite="data_label_overwrite"
      @click="import_clicked">
    </loader-import-button>

  </v-container>
</template>