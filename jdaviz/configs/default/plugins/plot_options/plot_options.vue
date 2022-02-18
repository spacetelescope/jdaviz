<template>
  <j-tray-plugin>
    <v-row>
      <j-docs-link>Viewer and data/layer options.</j-docs-link>
    </v-row>

    <v-row v-if="viewer_items.length > 1">
      <v-select
        :items="viewer_items"
        v-model="selected_viewer"
        label="Viewer"
        hint="Select the viewer to set options."
        persistent-hint
      ></v-select>
    </v-row>

    <div v-if="selected_viewer">
      <j-plugin-section-header>Viewer Options</j-plugin-section-header>

      <v-row v-if="viewer_state_items.indexOf('show_axes') !== -1">
        <v-switch
          v-model="show_axes"
          label="Show axes"/>
      </v-row>

      <v-row v-if="viewer_state_items.indexOf('function') !== -1">
        <v-select
          :items="function_items"
          v-model="function_selected"
          label="Function"/>
      </v-row>

      <j-plugin-section-header>Layer Options</j-plugin-section-header>
      <v-row>
        <v-select
          :items="layer_items"
          v-model="selected_layer"
          label="Layer"
          hint="Select the data or subset to set options."
          persistent-hint
        ></v-select>
      </v-row>

    </div>

  </j-tray-plugin>
</template>
