<template>
  <div>
    <plugin-auto-label
      :label="label"
      @change="$emit('update:label', $event)"
      @update:label="$emit('update:label', $event)"
      :label_default="label_default"
      :auto="label_auto"
      @update:auto="$emit('update:label_auto', $event)"
      :label_invalid="label_invalid"
      :label_label="label_label ? label_label : 'Output Data Label'"
      :label_hint="label_hint ? label_hint : 'Label for the resulting data item.'"
    ></plugin-auto-label>   

    <plugin-viewer-select
      :items="add_to_viewer_items"
      :selected="add_to_viewer_selected"
      @update:selected="$emit('update:add_to_viewer_selected', $event)"
      show_if_single_entry="true"
      label='Plot in Viewer'
      :hint="add_to_viewer_hint ? add_to_viewer_hint : 'Plot results in the specified viewer.  Data entry will be available in the data dropdown for all applicable viewers.'"
    ></plugin-viewer-select>
  </div>
</template>
<script>
module.exports = {
  props: ['label', 'label_default', 'label_auto', 'label_invalid', 'label_label', 'label_hint',
          'add_to_viewer_items', 'add_to_viewer_selected', 'add_to_viewer_hint']
};
</script>
