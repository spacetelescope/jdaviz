<template>
<div>
  <plugin-select
    :items="col_ra_items.map(i => i.label)"
    :selected.sync="col_ra_selected"
    label="RA"
    hint="Select column corresponding to RA."
    api_hint="ldr.importer.col_ra ="
    :api_hints_enabled="api_hints_enabled"
  ></plugin-select>

  <plugin-select
    :items="col_dec_items.map(i => i.label)"
    :selected.sync="col_dec_selected"
    label="DEC"
    hint="Select column corresponding to Declination."
    api_hint="ldr.importer.col_dec ="
    :api_hints_enabled="api_hints_enabled"
  />


  <plugin-select
    :items="col_other_items.map(i => i.label)"
    :selected.sync="col_other_selected"
    :multiselect="col_other_multiselect"
    label="Other Columns"
    hint="Select other columns to load into the app."
    api_hint="ldr.importer.col_other ="
    :api_hints_enabled="api_hints_enabled"
  />

  <span>Table Preview</span>
  <v-data-table
    dense
    :headers="headers.map(item => {return {'text': item, 'value': item}})"
    :items="items"
    class="elevation-1 width-100"
  ></v-data-table>

  <v-row>
      <plugin-auto-label
        :value.sync="label_value"
        :default="label_default"
        :auto.sync="label_auto"
        :invalid_msg="label_invalid_msg"
        label="Catalog label"
        api_hint="ldr.importer.label ="
        :api_hints_enabled="api_hints_enabled"
        hint="Label to assign to the catalog."
      ></plugin-auto-label>
  </v-row>
</div>
</template>