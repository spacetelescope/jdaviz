<template>
<v-container>

  <j-plugin-section-header>Select coordinate columns</j-plugin-section-header>

  <div style="font-size: 10px; color: rgba(0, 0, 0, 0.6); margin-bottom: 5px;">
  Select RA/Dec and/or X/Y pair to enable import. Pixel positions
  are w.r.t the image viewer reference data.
  </div>

  <plugin-select
    :items="col_ra_items.map(i => i.label)"
    :selected.sync="col_ra_selected"
    label="RA"
    hint="Column corresponding to RA coordinate."
    api_hint="ldr.importer.col_ra ="
    :api_hints_enabled="api_hints_enabled"
  ></plugin-select>

 	<plugin-select v-if="!col_ra_has_unit"
    :items="col_ra_unit_items.map(i => i.label)"
    :selected.sync="col_ra_unit_selected"
    label="RA Unit"
    hint="Unit for RA coordinate."
    api_hint="ldr.importer.col_ra_unit ="
    :api_hints_enabled="api_hints_enabled"
 	></plugin-select>

  <plugin-select
    :items="col_dec_items.map(i => i.label)"
    :selected.sync="col_dec_selected"
    label="Dec"
    hint="Column corresponding to Dec. coordinate."
    api_hint="ldr.importer.col_dec ="
    :api_hints_enabled="api_hints_enabled"
  ></plugin-select>

  <plugin-select v-if="!col_dec_has_unit"
    :items="col_dec_unit_items.map(i => i.label)"
    :selected.sync="col_dec_unit_selected"
    label="Dec Unit"
    hint="Unit for Dec. coordinate"
    api_hint="ldr.importer.col_dec_unit ="
    :api_hints_enabled="api_hints_enabled"
  ></plugin-select>

  <plugin-select
    :items="col_x_items.map(i => i.label)"
    :selected.sync="col_x_selected"
    label="X Column"
    hint="Column corresponding to X coordinate."
    api_hint="ldr.importer.col_x ="
    :api_hints_enabled="api_hints_enabled"
  ></plugin-select>

    <plugin-select
    :items="col_y_items.map(i => i.label)"
    :selected.sync="col_y_selected"
    label="Y Column"
    hint="Column corresponding to Y coordinate."
    api_hint="ldr.importer.col_y ="
    :api_hints_enabled="api_hints_enabled"
  ></plugin-select>

  <j-plugin-section-header>Select Source ID Column</j-plugin-section-header>
  <plugin-select
    :items="col_id_items.map(i => i.label)"
    :selected.sync="col_id_selected"
    label="Source ID Column"
    hint="Select column to use as source IDs (displayed on mouseover for image/scatter viewers)."
    api_hint="ldr.importer.col_id ="
    :api_hints_enabled="api_hints_enabled"
  />

  <j-plugin-section-header>Select Additional Columns</j-plugin-section-header>
  <plugin-select
    :items="col_other_items.map(i => i.label)"
    :selected.sync="col_other_selected"
    :multiselect="col_other_multiselect"
    label="Other Columns"
    hint="Select additional columns to load."
    api_hint="ldr.importer.col_other ="
    :api_hints_enabled="api_hints_enabled"
  />

  <plugin-auto-label
    :value.sync="data_label_value"
    :default="data_label_default"
    :auto.sync="data_label_auto"
    :invalid_msg="data_label_invalid_msg"
    label="Catalog label"
    api_hint="ldr.importer.label ="
    :api_hints_enabled="api_hints_enabled"
    hint="Label to assign to the catalog."
  ></plugin-auto-label>

  <plugin-viewer-create-new
    :items="viewer_items"
    :selected.sync="viewer_selected"
    :create_new_items="viewer_create_new_items"
    :create_new_selected.sync="viewer_create_new_selected"
    :new_label_value.sync="viewer_label_value"
    :new_label_default="viewer_label_default"
    :new_label_auto.sync="viewer_label_auto"
    :new_label_invalid_msg="viewer_label_invalid_msg"
    :multiselect="viewer_multiselect"
    :show_multiselect_toggle="false"
    label="Viewer"
    api_hint='ldr.importer.viewer = '
    :api_hints_enabled="api_hints_enabled"
    :show_if_single_entry="true"
    hint="Select the viewer to use for the new data entry."
  ></plugin-viewer-create-new>

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