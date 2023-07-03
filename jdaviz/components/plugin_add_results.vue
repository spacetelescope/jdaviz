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
        label='Plot in Viewer'
        :hint="add_to_viewer_hint ? add_to_viewer_hint : 'Plot results in the specified viewer.  Data entry will be available in the data dropdown for all applicable viewers.'"
      ></plugin-viewer-select>
    </div>

    <v-row v-else>
      <v-switch v-if="label_overwrite"
        class="hide-input"
        :label="'Show in '+add_to_viewer_items[1].label"
        :disabled="true"
        :hint="'Visibility of the modified entry will be adopted from the current \''+label+'\' data entry.'"
        persistent-hint
      >
      </v-switch>
      <v-switch v-else
        v-model="add_to_viewer_selected == this.add_to_viewer_items[1].label"
        @change="(e) => {$emit('update:add_to_viewer_selected', this.$props.add_to_viewer_items[Number(e)].label)}"
        :label="'Show in '+add_to_viewer_items[1].label"
        hint='Immediately plot results.  Data entry will be available to toggle in the data dropdown'
        persistent-hint
      >
      </v-switch>
    </v-row>

    <slot></slot>

    <v-row justify="end">
      <j-tooltip :tooltipcontent="label_overwrite ? action_tooltip+' and replace existing entry' : action_tooltip">
        <v-btn :disabled="label_invalid_msg.length > 0 || action_disabled"
          text
          color="accent"
          @click="$emit('click:action')"
        >{{action_label}}{{label_overwrite ? ' (Overwrite)' : ''}}
        </v-btn>
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
  props: ['label', 'label_default', 'label_auto', 'label_invalid_msg', 'label_overwrite', 'label_label', 'label_hint',
          'add_to_viewer_items', 'add_to_viewer_selected', 'add_to_viewer_hint',
          'action_disabled', 'action_label', 'action_tooltip']
};
</script>
