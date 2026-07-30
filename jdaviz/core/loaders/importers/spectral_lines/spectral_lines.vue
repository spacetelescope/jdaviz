<template>
  <v-container>

    <j-plugin-section-header>Definitions</j-plugin-section-header>

    <plugin-select
      :items="spectral_loc_items.map(i => i.label)"
      v-model:selected="spectral_loc_selected"
      label="Spectral Location"
      hint="Column containing the spectral positions (e.g. wavelength, frequency, energy)."
      api_hint="ldr.importer.spectral_loc ="
      :api_hints_enabled="api_hints_enabled"
    ></plugin-select>

    <plugin-select v-if="!spectral_loc_has_unit"
      :items="spectral_loc_unit_items.map(i => i.label)"
      v-model:selected="spectral_loc_unit_selected"
      label="Spectral Unit"
      hint="Unit for the spectral location column."
      api_hint="ldr.importer.spectral_loc_unit ="
      :api_hints_enabled="api_hints_enabled"
    ></plugin-select>

    <plugin-select
      :items="medium_items.map(i => i.label)"
      v-model:selected="medium_selected"
      label="Medium"
      hint="Medium in which the spectral line positions are defined."
      api_hint="ldr.importer.medium ="
      :api_hints_enabled="api_hints_enabled"
    ></plugin-select>

    <j-plugin-section-header>Select Additional Columns</j-plugin-section-header>
    <plugin-select
      :items="col_other_items.map(i => i.label)"
      v-model:selected="col_other_selected"
      :multiselect="col_other_multiselect"
      label="Other Columns"
      hint="Select additional columns to include in the loaded table."
      api_hint="ldr.importer.col_other ="
      :api_hints_enabled="api_hints_enabled"
    />

    <plugin-auto-label
      v-model:value="data_label_value"
      :default="data_label_default"
      v-model:auto="data_label_auto"
      :invalid_msg="data_label_invalid_msg"
      label="Line list label"
      api_hint="ldr.importer.label ="
      :api_hints_enabled="api_hints_enabled"
      hint="Label to assign to the line list in the data collection."
    ></plugin-auto-label>

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
      hint="Select the viewer to display the line list in."
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
