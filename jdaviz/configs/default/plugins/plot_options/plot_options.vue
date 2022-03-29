<template>
  <j-tray-plugin>
    <v-row>
      <j-docs-link :link="'https://jdaviz.readthedocs.io/en/'+vdocs+'/'+config+'/plugins.html#plot-options'">Viewer and data/layer options.</j-docs-link>
    </v-row>

    <plugin-viewer-select
      :items="viewer_items"
      :selected.sync="viewer_selected"
      label="Viewer"
      hint="Select the viewer to set options."
    />

    <div v-if="viewer_selected">
      <j-plugin-section-header>Viewer Options</j-plugin-section-header>
      <v-row class="row-no-outside-padding">
        <jupyter-widget v-if="viewer_selected" :widget="viewer_widget"></jupyter-widget>
      </v-row>

      <v-row v-if="has_show_uncertainty">
        <v-switch
            v-model="show_uncertainty"
            label="Plot Uncertainty"
            hint="Show uncertainty values in the y-axis above and below the spectrum."
            persistent-hint>
        </v-switch>
      </v-row>
      
      <j-plugin-section-header>Layer Options</j-plugin-section-header>      
      <v-row class="row-no-outside-padding">
        <jupyter-widget v-if="viewer_selected" :widget="layer_widget"></jupyter-widget>
      </v-row>
    </div>

  </j-tray-plugin>
</template>
