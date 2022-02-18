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
        <jupyter-widget v-if="selected_viewer" :widget="viewer_widget" ref="viewer_widget"></jupyter-widget>
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
      
      <v-row class="row-no-outside-padding">
        <jupyter-widget v-if="selected_layer" :widget="layer_widget" ref="layer_widget"></jupyter-widget>
      </v-row>
    </div>

  </j-tray-plugin>
</template>

<script>
module.exports = {
  mounted() {
    this.hideUnwanted = () => {
      // strip out any glue-items we don't want, by searching for their labels in the DOM
      const hideLabels = ['reference', 'x axis', 'y axis', 'equal aspect ratio', 'attribute'];
      var labelElements = [];
      var sliderDivElements = [];
      ['viewer_widget', 'layer_widget'].forEach((ref) => {
        labelElements = this.$refs[[ref]].$el.querySelectorAll("label");
        sliderDivElements = this.$refs[[ref]].$el.querySelectorAll(".slider-label");
        labelElements.forEach((el) => {
          if (hideLabels.indexOf(el.textContent) !== -1) {
            // go up the DOM and hide the v-input
            el.parentElement.parentElement.parentElement.parentElement.style.display = 'none';
          }
        })
        sliderDivElements.forEach((el) => {
          if (hideLabels.indexOf(el.textContent) !== -1 || el.textContent.startsWith("Wave")) {
            // go up the DOM and hide the parent (likely v-col)
            el.parentElement.style.display = 'none';
          }
        })
      });
    };  
    this.hideUnwanted();
  },
  updated() {
    this.hideUnwanted();
  },
}
</script>
