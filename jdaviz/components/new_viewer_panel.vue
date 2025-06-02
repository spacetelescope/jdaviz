<template>
  <div>
    <v-select
      :menu-props="{ left: true }"
      attach
      :items="new_viewer_items_filtered"
      v-model="new_viewer_selected"
      @change="$emit('update:new_viewer_selected', $event)"
      label="Viewer Type"
      hint="Select new viewer type"
      item-text="label"
      item-value="label"
      persistent-hint
      outlined
      style="width: 100%; margin-top: 12px; padding-left: 6px; padding-right: 6px;"
    ></v-select>

    <v-container>
      <v-row>
        <v-alert v-if="new_viewer_items_filtered.length === 0" type="warning" style="margin-left: 12px; margin-right: 12px;">
          Add data before creating viewers.
        </v-alert>
      </v-row>

      <span v-if="new_viewer_selected.length > 0 && api_hints_enabled" class="api-hint" style="font-weight: bold; padding-left: 6px">
        vc = {{ api_hints_obj }}.new_viewers['{{ new_viewer_selected }}']
      </span>
    </v-container>

    <jupyter-widget v-if="new_viewer_selected.length > 0" :widget="new_viewer_items.find((new_viewer) => new_viewer.label === new_viewer_selected).widget"></jupyter-widget>

  </div>
</template>

<script>
module.exports = {
  props: ['new_viewer_items', 'new_viewer_selected', 'api_hints_enabled', 'api_hints_obj'],
  computed: {
    new_viewer_items_filtered() {
      return this.new_viewer_items.filter(item => item.is_relevant);
    },
  },
}
</script>

<style scoped>
.v-slide-group__wrapper {
  width: 150px;
}
</style>