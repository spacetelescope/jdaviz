<template>
  <div>
    <plugin-auto-label
      :value="label"
      @change="$emit('update:label', $event)"
      @update:value="$emit('update:label', $event)"
      :default="label_default"
      :auto="label_auto"
      @update:auto="$emit('update:label_auto', $event)"
      :invalid_msg="label_invalid_msg"
      :label="label_label ? label_label : 'Output Data Label'"
      :api_hint="add_results_api_hint && add_results_api_hint + '.label ='"
      :api_hints_enabled="api_hints_enabled && add_results_api_hint"
      :hint="label_hint ? label_hint : 'Label for the resulting data item.'"
    ></plugin-auto-label>   

    <div v-if="add_to_viewer_items.length > 2">
      <v-switch v-if="label_overwrite"
        class="hide-input"
        label="Show in viewers"
        :disabled="true"
        :hint="'Visibility of the modified entry will be adopted from the current \''+label+'\' data entry.'"
        persistent-hint
      >
      </v-switch>
      <plugin-viewer-select v-else
        :items="add_to_viewer_items"
        :selected="add_to_viewer_selected"
        @update:selected="$emit('update:add_to_viewer_selected', $event)"
        show_if_single_entry="true"
        label="Plot in Viewer"
        :api_hint="add_results_api_hint && add_results_api_hint+'.viewer ='"
        :api_hints_enabled="api_hints_enabled && add_results_api_hint"
        :hint="add_to_viewer_hint ? add_to_viewer_hint : 'Plot results in the specified viewer.  Data entry will be available in the data dropdown for all applicable viewers.'"
      ></plugin-viewer-select>
    </div>

    <v-row v-else>
      <v-switch v-if="label_overwrite"
        :label="addToViewerText"
        :class="api_hints_enabled && add_results_api_hint ? 'api-hint hide-input' : 'hide-input'"
        :disabled="true"
        :hint="'Visibility of the modified entry will be adopted from the current \''+label+'\' data entry.'"
        persistent-hint
      >
      </v-switch>
      <v-switch v-else
        v-model="add_to_viewer_selected == this.add_to_viewer_items[1].label"
        @change="(e) => {$emit('update:add_to_viewer_selected', this.$props.add_to_viewer_items[Number(e)].label)}"
        :label="addToViewerText"
        :class="api_hints_enabled && add_results_api_hint ? 'api-hint' : null"
        hint='Immediately plot results.  Data entry will be available to toggle in the data dropdown'
        persistent-hint
      >
      </v-switch>
    </v-row>

    <slot></slot>

    <!-- currently not exposed to users, uncomment this block and include in the 
         user API for the AutoUpdate component to re-enable
    <v-row v-if="auto_update_result !== undefined">
      <v-switch
        v-model="auto_update_result"
        @change="(e) => {$emit('update:auto_update_result', auto_update_result)}"
        label="Auto-update result"
        hint="Regenerate the resulting data-product whenever any inputs are changed"
        persistent-hint
      >
      </v-switch>
    </v-row>
    -->

    <v-row justify="end">
      <j-tooltip :tooltipcontent="label_overwrite ? action_tooltip+' and replace existing entry' : action_tooltip">
        <plugin-action-button 
          :spinner="action_spinner"
          :disabled="label_invalid_msg.length > 0 || action_disabled"
          :results_isolated_to_plugin="false"
          :api_hints_enabled="api_hints_enabled && action_api_hint"
          @click="$emit('click:action')">
          {{ actionButtonText }}
        </plugin-action-button>
      </j-tooltip>
    </v-row>
  </div>
</template>

<style scoped>
  .hide-input .v-input--selection-controls__input {
    opacity: 0;
  }
</style>

<script>
  module.exports = {
    props: ['add_results_api_hint',
            'label', 'label_default', 'label_auto', 'label_invalid_msg', 'label_overwrite', 'label_label', 'label_hint',
            'add_to_viewer_items', 'add_to_viewer_selected', 'add_to_viewer_hint', 'auto_update_result',
            'action_disabled', 'action_spinner', 'action_label', 'action_api_hint', 'action_tooltip', 'api_hints_enabled'],
    computed: {
      actionButtonText() {
        if (this.api_hints_enabled && this.action_api_hint) {
          return this.action_api_hint;
        } else if (this.label_overwrite) {
          return this.action_label + ' (Overwrite)';
        } else {
          return this.action_label;
        }
      },
      addToViewerText() {
        if (this.api_hints_enabled && this.add_results_api_hint) {
          return this.add_results_api_hint + '.viewer = \'' + this.add_to_viewer_selected+'\'';
        } else {
          return 'Show in ' + this.add_to_viewer_items[1].label;
        }
      }
    }
};
</script>
