<template>
  <v-container>
    <!-- TODO: FIX THE HINT -->
    <!-- api_hint="ldr.exposure_nums =" -->
    <div v-if="!disable_dropdown && exposures_items.length > 0">
      <plugin-select
        :items="exposures_items.map(i => i.label)"
        :selected.sync="exposures_selected"
        :show_if_single_entry="true"
        :multiselect="exposures_multiselect"
        :search="true"
        label="Exposure"
        api_hint="ldr.exposures ="
        :api_hints_enabled="api_hints_enabled"
        hint="Exposures to select from."
      ></plugin-select>
    </div>

    <div style="height: 8px;"></div>

    <div v-if="!disable_dropdown">
      <plugin-select
        :items="source_id_dropdown_items"
        :selected.sync="spectra_selected"
        :show_if_single_entry="true"
        :multiselect="spectra_multiselect"
        :search="true"
        label="Source IDs"
        api_hint="ldr.source_ids ="
        :api_hints_enabled="api_hints_enabled"
        hint="Source IDs to select from the list of spectra."
      ></plugin-select>
    </div>

    <div style="height: 16px;"></div>

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
  props: {
    exposure_items: Array,
    spectra_items: Array,
    exposure_selected: Array,
    exposure_multiselect: Boolean,
    spectra_selected: Array,
    spectra_multiselect: Boolean,
    disable_dropdown: Boolean,
    api_hints_enabled: Boolean,
    data_label_value: String,
    data_label_default: String,
    data_label_auto: Boolean,
    data_label_invalid_msg: String
  },
  computed: {
    filtered_spectra_items() {
      // If no exposure selected, show all
      if (!this.exposures_selected || this.exposures_selected.length === 0) {
        return this.spectra_items;
      }
      // Extract exposure numbers from selected ver
      const selectedExposures = this.exposures_selected.map(label => {
        // Assumes label format: "Exposure N"
        const match = label.match(/Exposure (\d+)/);
        return match ? match[1] : null;
      }).filter(Boolean);
      // Filter spectra_items by ver (exposure number)
      return this.spectra_items.filter(item => {
        // Assumes item.ver is a string or number representing exposure number
        return selectedExposures.includes(String(item.ver));
      });
    },
    source_id_dropdown_items() {
      // Union of filtered source IDs and currently selected source IDs
      const filteredLabels = this.filtered_spectra_items.map(i => i.label);
      const selectedLabels = Array.isArray(this.spectra_selected) ? this.spectra_selected : [];
      // Merge and deduplicate
      return Array.from(new Set([...filteredLabels, ...selectedLabels]));
    }
  }
}
</script>
