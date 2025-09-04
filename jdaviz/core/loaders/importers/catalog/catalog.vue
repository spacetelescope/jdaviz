<template>
<v-container>
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

  <v-row>
    <plugin-switch
        :value.sync="cone_search"
        label="Filter by cone search"
        api_hint="ldr.cone_search = "
        :api_hints_enabled="api_hints_enabled"
        hint="Filter catalog by cone search before loading."
      />
  </v-row>

  <v-row v-if="cone_search">
    <v-text-field
        ref="cone_search_ra"
        type="number"
        :label="api_hints_enabled ? 'ldr.cone_search_ra =' : 'Cone RA'"
        :class="api_hints_enabled ? 'api-hint' : null"
        v-model.number="cone_search_ra"
        hint="Cone search RA (degs)."
        persistent-hint
        :rules="[() => cone_search_ra !== '' || 'This field is required']"
      ></v-text-field>
  </v-row>

  <v-row v-if="cone_search">
    <v-text-field
        ref="cone_search_dec"
        type="number"
        :label="api_hints_enabled ? 'ldr.cone_search_dec =' : 'Cone DEC'"
        :class="api_hints_enabled ? 'api-hint' : null"
        v-model.number="cone_search_dec"
        hint="Cone search DEC (degs)."
        persistent-hint
        :rules="[() => cone_search_dec !== '' || 'This field is required']"
      ></v-text-field>
  </v-row>

  <v-row v-if="cone_search">
    <v-text-field
        ref="cone_search_radius"
        type="number"
        :label="api_hints_enabled ? 'ldr.cone_search_radius =' : 'Cone Radius'"
        :class="api_hints_enabled ? 'api-hint' : null"
        v-model.number="cone_search_radius"
        hint="Cone search radius in arcmin."
        persistent-hint
        :rules="[() => cone_search_radius !== '' || 'This field is required',
                 () => cone_search_radius >=0 || 'Cone radius must be positive']"
      ></v-text-field>
  </v-row>

  <plugin-section-header>Table Preview</plugin-section-header>

  <v-row>
    <v-data-table
      dense
      :headers="headers.map(item => {return {'text': item, 'value': item}})"
      :items="items"
      class="elevation-1 width-100"
    ></v-data-table>
  </v-row>

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
</v-container>
</template>