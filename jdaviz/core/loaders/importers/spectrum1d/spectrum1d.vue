<template>
  <v-container>
    <plugin-select
      :items="extension_items"
      :selected.sync="extension_selected"
      :show_if_single_entry="true"
      :multiselect="multiselect"
      :exists_in_dc="existing_data_in_dc"
      label="Extension"
      api_hint="ldr.importer.extension ="
      :api_hints_enabled="api_hints_enabled"
      hint="Extension to use for the data."
    ></plugin-select>

    <plugin-switch
      v-if="multiselect && extension_selected.length > 1"
      :value.sync="concatenate"
      label="Concatenate"
      api_hint="ldr.importer.concatenate ="
      :api_hints_enabled="api_hints_enabled"
      hint="Concatenate multiple selected spectra into a single spectrum."
    ></plugin-switch>

    <plugin-auto-label
      :value.sync="data_label_value"
      :default="data_label_default"
      :auto.sync="data_label_auto"
      :invalid_msg="data_label_invalid_msg"
      label="Data Label"
      api_hint="ldr.importer.data_label ="
      :api_hints_enabled="api_hints_enabled"
      :hint="data_label_is_prefix ? 'Prefix to assign to the new data entry.  Will resolve to the following data labels:' : 'Label to assign to the new data entry.'"
    >
    </plugin-auto-label>
    <v-row v-if="data_label_is_prefix">
        <j-tooltip v-for="(suff, index) in data_label_suffices"
          :key="suff"
          :tooltipcontent="data_label_overwrite_by_index[index] ? 'Will overwrite existing entry' : 'New entry'">
          <v-chip
            outlined
            label
            style="margin: 4px"
          >
            <v-icon v-if="data_label_overwrite_by_index[index]" small left color="warning">mdi-file-replace</v-icon>
            {{data_label_value}}{{suff}}
          </v-chip>
        </j-tooltip>
    </v-row>

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
      api_hint="ldr.importer.viewer ="
      :api_hints_enabled="api_hints_enabled"
      :show_if_single_entry="true"
      hint="Select the viewer to use for the new data."
    ></plugin-viewer-create-new>

    <v-row justify="end">
      <j-tooltip :tooltipcontent="data_label_overwrite ? 'Import and replace existing entries' : 'Import data'">
        <plugin-action-button
          :spinner="import_spinner"
          :disabled="import_disabled || extension_selected.length === 0"
          :results_isolated_to_plugin="false"
          :api_hints_enabled="api_hints_enabled"
          @click="import_clicked">
          {{ api_hints_enabled ?
            'ldr.load()'
            :
            importButtonText
          }}
        </plugin-action-button>
      </j-tooltip>
    </v-row>

  </v-container>
</template>

<script>
module.exports = {
  computed: {
    overwriteCount() {
      if (!this.data_label_overwrite_by_index) return 0;
      return this.data_label_overwrite_by_index.filter(x => x).length;
    },
    importButtonText() {
      if (this.data_label_is_prefix && this.overwriteCount > 0) {
        return 'Import (overwrite ' + this.overwriteCount + '/' + this.data_label_suffices.length + ')';
      } else if (this.data_label_overwrite) {
        return 'Import (overwrite)';
      }
      return 'Import';
    }
  }
};
</script>