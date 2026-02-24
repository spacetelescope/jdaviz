<template>
  <v-row v-if="loader_items.length > 0">
    <v-expansion-panels accordion focusable v-model="loader_panel_ind" @change="$emit('update:loader_panel_ind', $event)">
      <v-expansion-panel>
        <v-expansion-panel-title v-slot="{ open }">
          <span style="padding: 6px">{{ title }}</span>
        </v-expansion-panel-title>
        <v-expansion-panel-text class="plugin-expansion-panel-content">
          <j-loader-panel
            :loader_items="loader_items"
            v-model:loader_selected="loader_selected"
            :api_hints_enabled="api_hints_enabled"
            :api_hints_obj="api_hints_obj"
            :hide_resolver="hide_resolver"
          ></j-loader-panel>
        </v-expansion-panel-text>
      </v-expansion-panel>
    </v-expansion-panels>
  </v-row>
</template>

<script>
export default {
  props: {
    loader_panel_ind: {},
    loader_items: {},
    loader_selected: {},
    api_hints_enabled: {},
    api_hints_obj: {},
    title: {
      type: String,
      default: 'Import'
    },
    hide_resolver: {}
  }
}
</script>
