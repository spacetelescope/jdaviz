<template>
  <v-row v-if="loader_items.length > 0">
    <v-expansion-panels
      accordion
      focusable
      :model-value="loader_panel_ind"
      @update:modelValue="$emit('update:loader_panel_ind', $event)"
    >
      <v-expansion-panel>
        <v-expansion-panel-title v-slot="{ open }">
          <span style="padding: 6px">Import</span>
        </v-expansion-panel-title>
        <v-expansion-panel-text class="plugin-expansion-panel-content">
          <j-loader-panel
            :loader_items="loader_items"
            :loader_selected="loader_selected"
            @update:loader_selected="$emit('update:loader_selected', $event)"
            :api_hints_enabled="api_hints_enabled"
            api_hints_obj="plg"
          ></j-loader-panel>
        </v-expansion-panel-text>
      </v-expansion-panel>
    </v-expansion-panels>
  </v-row>
</template>

<script>
export default {
  props: ['loader_panel_ind', 'loader_items', 'loader_selected', 'api_hints_enabled'],
}
</script>
