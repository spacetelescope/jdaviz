<template>
  <v-container>

      <div class="invert-if-dark" style="font-size: 10px; color: rgba(0, 0, 0, 0.6); margin-bottom: 5px;">
        Load generic tabular data into the data collection. For catalogs with
        source positions (e.g. RA/Dec or x/y pixel) or spectral lines, use the
        "Source Catalog" or "Spectral Lines" formats, respectively, to enable
        their specialized features.
      </div>
    <plugin-select v-if="extension_items.length"
      :items="extension_items"
      :exists_in_dc="existing_data_in_dc"
      v-model:selected="extension_selected"
      :show_if_single_entry="true"
      :multiselect="extension_multiselect"
      :search="extension_items.length > 3"
      label="Extension"
      api_hint="ldr.importer.extension ="
      :api_hints_enabled="api_hints_enabled"
      hint="Table extension(s) to import. If multiple selected, only columns common to all selected tables will be available for import. If column names differ, it is recommended to load tables individually."
    ></plugin-select>

    <div v-if="no_common_col_msg !== ''" style="font-size: 10px; color: red; margin-bottom: 5px;">
      {{ no_common_col_msg }}
    </div>

    <div v-if="!input_has_extensions || (extension_selected && extension_selected.length > 0 && no_common_col_msg === '')">

      <j-plugin-section-header>Select Columns</j-plugin-section-header>
      <plugin-select
        :items="col_other_items.map(i => i.label)"
        v-model:selected="col_other_selected"
        :multiselect="col_other_multiselect"
        label="Columns"
        hint="Select columns to load."
        api_hint="ldr.importer.col_other ="
        :api_hints_enabled="api_hints_enabled"
      />

      <plugin-auto-label
      v-model:value="data_label_value"
      :default="data_label_default"
      v-model:auto="data_label_auto"
      :invalid_msg="data_label_invalid_msg"
      label="Catalog label"
      api_hint="ldr.importer.data_label ="
      :api_hints_enabled="api_hints_enabled"
      hint="Label to assign to the catalog."
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

    </div>

  </v-container>
</template>

