<template>
  <v-row justify="end">
    <j-tooltip :tooltipcontent="tooltipText">
      <plugin-action-button
        :spinner="spinner"
        :disabled="disabled"
        :results_isolated_to_plugin="false"
        :api_hints_enabled="api_hints_enabled"
        @click="$emit('click')">
        {{ api_hints_enabled ? api_hint : buttonText }}
      </plugin-action-button>
    </j-tooltip>
  </v-row>
</template>

<script>
module.exports = {
  props: ['spinner', 'disabled', 'api_hints_enabled', 'api_hint',
          'data_label_overwrite', 'data_label_is_prefix',
          'data_label_suffices', 'data_label_overwrite_by_index'],
  computed: {
    overwriteCount() {
      if (!this.data_label_overwrite_by_index) return 0;
      return this.data_label_overwrite_by_index.filter(x => x).length;
    },
    buttonText() {
      if (this.data_label_is_prefix && this.overwriteCount > 0) {
        return 'Import (overwrite ' + this.overwriteCount + '/' + this.data_label_suffices.length + ')';
      } else if (this.data_label_overwrite) {
        return 'Import (overwrite)';
      }
      return 'Import';
    },
    tooltipText() {
      if (this.data_label_is_prefix && this.overwriteCount > 0) {
        return 'Import and replace ' + this.overwriteCount + ' existing entries';
      } else if (this.data_label_overwrite) {
        return 'Import and replace existing entry';
      }
      return 'Import data';
    }
  }
};
</script>
