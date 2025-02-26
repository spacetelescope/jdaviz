<template>
  <v-row>
    <v-expansion-panels accordion focusable v-model="loader_panel_ind" @change="$emit('update:loader_panel_ind', $event)">
      <v-expansion-panel>
        <v-expansion-panel-header v-slot="{ open }">
          <span style="padding: 6px">Import</span>
        </v-expansion-panel-header>
        <v-expansion-panel-content class="plugin-expansion-panel-content">
          <j-loader-panel
            :loader_items="loader_items"
            :loader_selected.sync="loader_selected"
            :api_hints_enabled="api_hints_enabled"
            api_hints_obj="plg"
          ></j-loader-panel>
        </v-expansion-panel-content>
      </v-expansion-panel>
    </v-expansion-panels>
  </v-row>
</template>

<script>
module.exports = {
  props: ['loader_panel_ind', 'loader_items', 'loader_selected', 'api_hints_enabled'],
}
</script>