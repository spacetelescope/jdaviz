<template>
</template>
<script>
export default {
  created() {
    this.$vuetify.theme.themes.light = {
      toolbar: "#153A4B",
      primary: "#00617E",
      secondary: "#007DA4",
      accent: "#C75109",
      turquoise: "#007BA1",
      lightblue: "#E3F2FD",  // matches highlighted row in MOS table
      spinner: "#163C4C",
      error: '#FF5252',
      info: '#2196F3',
      success: '#4CAF50',
      warning: '#FFC107',
      gray: '#F8F8F8',
    };
    this.$vuetify.theme.themes.dark = {
      toolbar: "#153A4B",
      primary: "#53CBFF",
      secondary: "#007DA4",
      accent: "#FF9D42",
      turquoise: "#007BA1",
      lightblue: "#E3F2FD",
      spinner: "#ACE1FF",
      error: '#FF5252',
      info: '#2196F3',
      success: '#4CAF50',
      warning: '#FFC107',
      gray: '#141414',
    };
  },
}
</script>

<style id="jdaviz-main-styles" >
* {
  /* otherwise, voila will override box-sizing to unset which screws up layouts */
  box-sizing: border-box !important;
}

/* fix for loading overlay z-index */
div.output_wrapper {
  z-index: auto;
}

.jd-loading-overlay {
  position: absolute;
  inset: 0;
  background-color: white;
  z-index: 100;
  opacity: 0.5;
}

.v-toolbar__content,
.vuetify-styles .v-toolbar__content {
  padding: 0px;
}

.plugin-expansion-panel-content .row {
  /* override -12px margins */
  margin-left: 0px;
  margin-right: 0px;
}

.glue__subset-select {
  display: flex;
  align-items: center;
}

.v-tabs-items {
  height: 100%;
}

.splitpanes {
  background-color: #f8f8f8;
}

.splitpanes__splitter {
  background-color: #e2e4e8;
  position: relative;
  width: 5px;
}

.lm_goldenlayout {
  background: #f8f8f8;
}

.lm_content {
  background: #ffffff;
  border: none;
  /*border-top: 1px solid #cccccc;*/
}

.lm_splitter {
  background: #e2e4e8;
  opacity: 1;
  z-index: 1;
}

/* .lm_splitter.lm_vertical {
  height: 1px !important;
}

.lm_splitter.lm_horizontal {
  width: 1px !important;
} */

.lm_header .lm_tab {
  padding-top: 0px;
  margin-top: 0px;
}

.lm_header ul {
  padding-left: 0;
}

.lm_popout {
  display: none;
}

.lm_close {
  /* hide the close button on the right (which allows closing an entire group of tabs) 
  so that we can control the ability to close tabs at the per-viewer level */
  display: none !important;
}

.cubeviz .lm_close_tab {
  /* do not allow closing any viewer tabs in cubeviz */
  display: none;
}

.imviz .lm_tab[title="imviz-0"] > .lm_close_tab {
  /* hide the close button on the tab for imviz-0 only to
     prevent closing the default viewer */
  display: none;
}

.v-toolbar__items .v-btn {
  /* allow v-toolbar-items styling to pass through tooltip wrapping span */
  /* css is copied from .v-toolbar__items>.v-btn */
  border-radius: 0;
  height: 100% !important;
  max-height: none;
}

.v-tooltip__content {
  background-color: white !important;
  border-radius: 2px !important;
  border: 1px #003B4D solid !important;
  color: black !important;
}

.v-expansion-panel-content__wrap {
  padding-left: 12px !important;
  padding-right: 12px !important;
}

a:link {
  text-decoration: none;
}

a:visited {
  text-decoration: none;
}

a:hover {
  text-decoration: none;
}

a:active {
  text-decoration: none;
}

.invert, .invert-if-dark.theme--dark {
  filter: invert(1) saturate(1) brightness(100);
  color: white;
}

.jdaviz-nested-toolbar, .plugin-nested-toolbar {
  /* height of nested toolbar to match viewer toolbar height */
  height: 42px;
  margin-right: 4px;
}

.jdaviz-nested-toolbar .v-icon, .jdaviz-nested-toolbar img {
  /* icons from dark to (consistently) light */
  filter: invert(1) saturate(1) brightness(100);
}

.jdaviz-nested-toolbar .v-btn, .plugin-nested-toolbar .v-btn {
  height: 42px !important;
  border: none !important;
  min-width: 42px !important;
  /* remove "dimming" since we use orange background for active */
  color: transparent ! important;
}

.suboptions-carrot {
  /* tweak margins for different toolbar size */
  margin-bottom: -28px !important;
}

.jdaviz-nested-toolbar .v-btn--active, .jdaviz-nested-toolbar .v-btn:focus, .v-toolbar .active, .jdaviz-viewer-toolbar .active {
  /* active color (orange) */
  background-color: #c75109 !important;
}

.plugin-nested-toolbar .v-btn--active, .plugin-nested-toolbar .v-btn:focus {
  /* semi-transparent active color (orange) */
  background-color: #c7510996 !important;
}

.v-divider.theme--dark {
  /* make the v-divider standout more */
  border-color: hsla(0,0%,100%,.35) !important;
}

.no-hint .v-text-field__details {
  display: none !important;
}

.color-to-accent {
  /* https://codepen.io/sosuke/pen/Pjoqqp for #C75109 */
  filter: brightness(0) saturate(100%) invert(31%) sepia(84%) saturate(1402%) hue-rotate(1deg) brightness(95%) contrast(94%);
}

.v-overlay__content {
  position: unset !important;
}

.jdaviz__content--not-in-notebook {
  max-height: calc(100% - 48px);
}

#popout-widget-container .v-application.jdaviz {
  min-height: 100vh;
  max-height: 100vh;
}

#popout-widget-container .jdaviz__content--not-in-notebook {
  max-height: 100%;
}

.jupyter-widgets.bqplot.figure {
  /* When a viewport is resized, a scrollbar can appear, which will impact the
   * render size of bqplot and results in unused space when the newly rendered
   * figure is displayed. Using overflow hidden will prevent the scrollbar from
   * appearing */
  overflow: hidden;
}

.jupyter-widgets.bqplot.figure .axislabel {
  /* consistent with other labels (legend, buttons, plugin expansion menu labels, etc)*/
  font-size: 15px !important;
  font-family: Roboto, sans-serif !important;
  font-weight: 500 !important;
}
</style>
