<template>
  <v-container>
    <div v-if="spectra_search" style="margin-bottom: 8px;">
      <v-text-field
          v-model="spectra_search_input"
          placeholder="Search Source IDs..."
          append-icon='mdi-magnify'
          style="width: 200px; margin-right: 8px; margin-top: 2px"
          dense
          clearable
          hide-details
          single-line
      ></v-text-field>
    </div>
    <plugin-select
      :items="filtered_spectra_items"
      :selected.sync="spectra_selected"
      :show_if_single_entry="true"
      :multiselect="spectra_multiselect"
      label="Source IDs"
      api_hint="ldr.source_ids ="
      :api_hints_enabled="api_hints_enabled"
      hint="Source IDs to select from the list of spectra."
    ></plugin-select>

    <v-row>
      <plugin-auto-label
        :value.sync="data_label_value"
        :default="data_label_default"
        :auto.sync="data_label_auto"
        :invalid_msg="data_label_invalid_msg"
        label="Data Label Prefix"
        api_hint="ldr.importer.data_label ="
        :api_hints_enabled="api_hints_enabled"
        hint="Prefix label to assign to the new data entries."
      ></plugin-auto-label>
    </v-row>
  </v-container>
</template>

<script>
export default {
  data() {
    return {
      spectra_search_input: ''
    };
  },
  computed: {
    filtered_spectra_items() {
      // Get selected as an array (handles both single and multi-select)
      const selected = Array.isArray(this.spectra_selected)
        ? this.spectra_selected
        : [this.spectra_selected];

      // Filter items by search
      let filtered = this.spectra_items.filter(i =>
        (i.label || '').toLowerCase().includes(this.spectra_search_input.toLowerCase())
      );

      // Add selected items not in filtered
      selected.forEach(sel => {
        if (
          sel &&
          !filtered.some(i => i.label === sel) &&
          this.spectra_items.some(i => i.label === sel)
        ) {
          filtered.push(this.spectra_items.find(i => i.label === sel));
        }
      });

      // Return as array of labels (if that's what your select expects)
      return filtered.map(i => i.label);
    }
  },
  props: {
    spectra_items: Array,
    spectra_selected: Array,
    spectra_multiselect: Boolean,
    api_hints_enabled: Boolean,
    data_label_value: String,
    data_label_default: String,
    data_label_auto: Boolean,
    data_label_invalid_msg: String
  }
};
</script>