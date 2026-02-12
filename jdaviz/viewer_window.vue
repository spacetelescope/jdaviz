<template>
  <div ref="top" class="jdaviz-viewer-window" style="width: 100%; height: 100%; overflow: hidden;">
    <div class="jdaviz-viewer-toolbar-container">
      <v-overlay
        v-if="viewer_destroyed"
        absolute
        opacity="0.85"
      >
        <v-alert color="error">This viewer has been closed at the app-level and this instance is no longer connected or functional.</v-alert>
      </v-overlay>
      <v-row dense style="background-color: #205f76; margin: 0px" class="jdaviz-viewer-toolbar">
        <j-tooltip v-if="config !== 'deconfigged'" tooltipcontent="data-menu is now opened by clicking on the legend in the top-right of the viewer">
          <v-btn
            text
            elevation="3"
            color="white"
            tile
            icon
            outlined
            style="height: 42px; width: 42px"
            @click="$emit('call-viewer-method', {'id': id, 'method': '_deprecated_data_menu'})"
            >
            <v-icon>mdi-format-list-bulleted-square</v-icon>
          </v-btn>
        </j-tooltip>

        <v-toolbar-items v-if="reference === 'table-viewer'">
          <j-tooltip tipid='table-prev'>
            <v-btn icon @click="$emit('call-viewer-method', {'id': id, 'method': 'prev_row'})" color="white">
              <v-icon>mdi-arrow-up-bold</v-icon>
            </v-btn>
          </j-tooltip>
          <j-tooltip tipid='table-next'>
            <v-btn icon @click="$emit('call-viewer-method', {'id': id, 'method': 'next_row'})" color="white">
              <v-icon>mdi-arrow-down-bold</v-icon>
            </v-btn>
          </j-tooltip>
        </v-toolbar-items>
        <j-play-pause-widget v-if="reference == 'table-viewer'" @event="$emit('call-viewer-method', {'id': id, 'method': 'next_row'})"></j-play-pause-widget>
        <v-spacer></v-spacer>
        <jupyter-widget class='jdaviz-nested-toolbar' :widget="toolbar_widget"></jupyter-widget>
        <span class='toolbar-popout-span' style="float: right; margin-top: 4px;">
          <j-plugin-popout :popout_button="popout_button"></j-plugin-popout>
        </span>
      </v-row>
    </div>

    <v-card tile flat style="width: 100%; height: calc(100% - 42px); overflow: hidden; overflow: hidden;">
      <jupyter-widget :widget="data_menu_widget"></jupyter-widget>
      <jupyter-widget
        :widget="figure_widget"
        :ref="'figure-widget-'+id"
        style="width: 100%; height: 100%; overflow: hidden;"
      ></jupyter-widget>
    </v-card>
  </div>
</template>

<script>
module.exports = {
  mounted() {
    this.ensureFullHeightChain();
  },
  methods: {
    ensureFullHeightChain() {
      const popoutSelector = ".jupyter-widgets-popout-container";
      const sidecarSelector = ".jp-LinkedOutputView .lm-Panel";

      const topElement = this.$refs.top;
      const fullHeightTarget = topElement.closest(sidecarSelector) || topElement.closest(popoutSelector);
      const fullWidthTarget = topElement.closest(".lm-Widget");

      let el = topElement.parentElement;
      /* timeout needed because the style of .lm-Widget is overwritten otherwise */
      setTimeout(() => {
        while (fullHeightTarget && el && el !== fullHeightTarget) {
          el.style.height = '100%';
          el = el.parentElement;
        }
        // Set width only on the first ancestor with class .lm-Widget
        if (fullWidthTarget) {
          fullWidthTarget.style.width = '100%';
        }
      }, 0);
    }
  },
}
</script>

<style scoped>
.toolbar-popout-span i {
  color: white !important;
}

</style>