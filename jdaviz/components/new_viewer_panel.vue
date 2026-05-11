<template>
  <div>
    <v-select
      :menu-props="{ left: true }"
      attach
      :items="new_viewer_items_filtered"
      :model-value="new_viewer_selected"
      @update:modelValue="$emit('update:new_viewer_selected', $event)"
      label="Viewer Type"
      hint="Select new viewer type"
      item-title="label"
      item-value="label"
      persistent-hint
      variant="outlined"
      style="width: 100%; margin-top: 12px; padding-left: 6px; padding-right: 6px;"
    ></v-select>

    <v-container>
      <j-flex-row>
        <v-alert v-if="new_viewer_items_filtered.length === 0" type="warning" style="margin-left: 12px; margin-right: 12px;">
          Add data before creating viewers.
        </v-alert>
      </j-flex-row>

      <span v-if="new_viewer_selected && new_viewer_selected.length > 0 && api_hints_enabled" class="api-hint" style="font-weight: bold; padding-left: 6px">
        vc = {{ api_hints_obj }}.new_viewers['{{ new_viewer_selected }}']
      </span>
    </v-container>

    <jupyter-widget v-if="selected_new_viewer_widget" :widget="selected_new_viewer_widget" :key="selected_new_viewer_widget"></jupyter-widget>

  </div>
</template>

<script>
export default {
  props: ['new_viewer_items', 'new_viewer_selected', 'api_hints_enabled', 'api_hints_obj'],
  computed: {
    new_viewer_items_filtered() {
      return this.new_viewer_items.filter(item => item.is_relevant);
    },
    selected_new_viewer_widget() {
      const newViewer = this.new_viewer_items.find(item => item.label === this.new_viewer_selected);
      return newViewer ? newViewer.widget : '';
    },
  },
}
</script>

<style scoped>
.v-slide-group__wrapper {
  width: 150px;
}
</style>
