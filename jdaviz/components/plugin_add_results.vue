<template>
  <div>
    <v-row>
      <v-text-field
        v-model="label"
        @change="$emit('update:label', $event)"
        @keydown="() => $emit('update:label_changed_by_user', true)"
        :label="label_label ? label_label : 'Output Data Label'"
        :hint="label_hint ? label_hint : 'Label for the resulting data item.'"
        persistent-hint
      ></v-text-field>
    </v-row>
    <plugin-viewer-select
      :items="add_to_viewer_items"
      :selected.sync="add_to_viewer_selected"
      show_if_single_entry="true"
      label='Plot in Viewer'
      :hint="add_to_viewer_hint ? add_to_viewer_hint : 'Plot results in the specified viewer.  Data entry will be available in the data dropdown for all applicable viewers.'"
    ></plugin-viewer-select>
  </div>
</template>
<script>
module.exports = {
  props: ['label', 'label_label', 'label_hint', 'add_to_viewer_items', 'add_to_viewer_selected', 'add_to_viewer_hint', 'label_changed_by_user']
};
</script>
