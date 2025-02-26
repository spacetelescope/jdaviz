<template>
  <v-dialog
      scrollable
      max-height="400px"
      width="700px"
      v-model="show_loader_dialog"
  >
    <template v-slot:activator="{ on }">
      <j-tooltip tooltipcontent="Import into plugin">
        <!-- NOTE: @click needed to propagate the change to the plugins show_loader_dialog traitlet -->
        <v-btn
          @click="$emit('update:show_loader_dialog', true)"
          tile
          depressed
          v-on="on"
          color="turquoise">
          Import (DEV)
        </v-btn>
      </j-tooltip>
    </template>
    <j-loader-dialog
      :use_tabs="true"
      :loader_items="loader_items"
      :loader_selected.sync="loader_selected"
      :api_hints_enabled="api_hints_enabled"
      :config="config"
    ></j-loader-dialog>
  </v-dialog>
</template>

<script>
module.exports = {
  props: ['show_loader_dialog', 'loader_items', 'loader_selected', 'api_hints_enabled', 'config'],
}
</script>