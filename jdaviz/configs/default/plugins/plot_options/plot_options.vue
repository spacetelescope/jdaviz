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
      <v-row class="row-no-outside-padding">
        <jupyter-widget v-if="selected_viewer" :widget="viewer_widget"></jupyter-widget>
      </v-row>
      
      <j-plugin-section-header>Layer Options</j-plugin-section-header>      
      <v-row class="row-no-outside-padding">
        <jupyter-widget v-if="selected_viewer" :widget="layer_widget"></jupyter-widget>
      </v-row>
    </div>

  </j-tray-plugin>
</template>
