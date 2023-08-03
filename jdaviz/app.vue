<template>
  <v-app id="web-app" :class="'jdaviz ' + config" ref="mainapp">
    <jupyter-widget
      v-if="state.style_widget"
      :widget="state.style_widget"
      style="display: none"
    ></jupyter-widget>
    <v-overlay v-if="state.logger_overlay"
      absolute
      opacity="0.7">
      <div :style="!state.settings.dense_toolbar ? 'position: absolute; top: 14px; right: 55px' : 'position: absolute; top: 6px; right: 55px'">
        <j-tooltip tipid="app-snackbar-history">
          <v-btn icon @click="state.logger_overlay = !state.logger_overlay" :class="{active : state.logger_overlay}">
            <v-icon medium style="padding-top: 2px">mdi-message-reply</v-icon>
          </v-btn>
        </j-tooltip>
      </div>
      <div :style="{'position': 'absolute',
                    'top': !state.settings.dense_toolbar ? '64px' : '48px',
                    'left': '0px',
                    'width': '100%',
                    'height': !state.settings.dense_toolbar ? 'calc(100% - 64px)' : 'calc(100% - 48px)',
                    'overflow-y': 'scroll',
                    'border-top': '6px solid #C75109',
                    'padding-left': '15%',
                    'padding-top': '20px'}"
            @click="state.logger_overlay = false">
        <v-row
            dense
            @click="(e) => {e.stopImmediatePropagation()}"
            v-for="history in state.snackbar_history.slice().reverse()"
            style="width: 80%">
          <v-alert
            dense
            :type="history.color"
            style="width: 100%; margin: 6px 0px 0px; text-align: left">
              [{{history.time}}]: {{history.text}}
          </v-alert>
        </v-row>
      </div>
    </v-overlay>
    <v-app-bar color="toolbar" dark :dense="state.settings.dense_toolbar" flat app absolute clipped-right style="margin-left: 1px; margin-right: 1px">
      <v-toolbar-items v-for="item in state.tool_items">
        <v-divider v-if="['g-data-tools', 'g-subset-tools'].indexOf(item.name) === -1" vertical style="margin: 0px 10px"></v-divider>
        <v-divider v-else-if="item.name === 'g-subset-tools'" vertical style="margin: 0px 10px; border-width: 0"></v-divider>
        <j-tooltip v-if="['cubeviz', 'mosviz'].indexOf(config) !== -1 && item.name == 'g-data-tools' && state.data_items.length !== 0"></j-tooltip>
        <j-tooltip v-else :tipid="item.name">
          <jupyter-widget :widget="item.widget" :key="item.name"></jupyter-widget>
        </j-tooltip>
      </v-toolbar-items>
      <v-spacer></v-spacer>
      <v-toolbar-items>
        <j-tooltip tipid="app-toolbar-popout">
          <jupyter-widget :widget="popout_button" ></jupyter-widget>
        </j-tooltip>
        <j-tooltip tipid="app-help">
          <v-btn icon :href="getReadTheDocsLink()" target="_blank">
            <v-icon medium>mdi-help-box</v-icon>
          </v-btn>
        </j-tooltip>
        <j-tooltip tipid="app-snackbar-history">
          <v-btn icon @click="state.logger_overlay = !state.logger_overlay" :class="{active : state.logger_overlay}">
            <v-icon medium style="padding-top: 2px">mdi-message-reply-text</v-icon>
          </v-btn>
        </j-tooltip>
        <j-tooltip tipid="app-toolbar-plugins">
          <v-btn icon @click="state.drawer = !state.drawer" :class="{active : state.drawer}">
            <v-icon>mdi-menu</v-icon>
          </v-btn>
        </j-tooltip>
      </v-toolbar-items>
    </v-app-bar>

    <v-content
      :style="checkNotebookContext() ? 'height: ' + state.settings.context.notebook.max_height + '; border: solid 1px #e5e5e5; border-top: 0px' : ''"
      :class="checkNotebookContext() ? '' : 'jdaviz__content--not-in-notebook'"
    >
      <v-container class="fill-height pa-0" fluid>
        <splitpanes>
          <pane size="75">
            <golden-layout
              style="height: 100%;"
              :has-headers="state.settings.visible.tab_headers"
              @state="onLayoutChange"
            >
              <gl-row :closable="false">
                <g-viewer-tab
                  v-for="(stack, index) in state.stack_items"
                  :stack="stack"
                  :key="stack.viewers.map(v => v.id).join('-')"
                  :data_items="state.data_items"
                  :app_settings="state.settings"
                  :icons="state.icons"
                  :viewer_icons="state.viewer_icons"
                  :layer_icons="state.layer_icons"
                  :closefn="destroy_viewer_item"
                  @data-item-visibility="data_item_visibility($event)"
                  @data-item-unload="data_item_unload($event)"
                  @data-item-remove="data_item_remove($event)"
                  @call-viewer-method="call_viewer_method($event)"
                ></g-viewer-tab>
              </gl-row>
            </golden-layout>
          </pane>
          <pane size="25" min-size="25" v-if="state.drawer" style="background-color: #fafbfc; border-top: 6px solid #C75109">
            <v-card flat tile class="overflow-y-auto fill-height" style="overflow-x: hidden" color="gray">
              <v-text-field
                v-model='state.tray_items_filter'
                append-icon='mdi-magnify'
                style="padding: 0px 8px"
                clearable
                hide-details
              ></v-text-field>
              <v-expansion-panels accordion multiple focusable flat tile v-model="state.tray_items_open">
                <v-expansion-panel v-for="(trayItem, index) in state.tray_items" :key="index">
                  <div v-if="trayItemVisible(trayItem, state.tray_items_filter)">
                    <v-expansion-panel-header >
                      <j-tooltip :tipid="trayItem.name">
                        {{ trayItem.label }}
                      </j-tooltip>
                    </v-expansion-panel-header>
                    <v-expansion-panel-content style="margin-left: -12px; margin-right: -12px;">
                      <jupyter-widget :widget="trayItem.widget" v-if="state.tray_items_open.includes(index)"></jupyter-widget>
                    </v-expansion-panel-content>
                  </div>
                </v-expansion-panel>
              </v-expansion-panels>
              <v-divider></v-divider>
            </v-card>
          </pane>
        </splitpanes>
      </v-container>
    </v-content>
    <v-snackbar
      v-model="state.snackbar.show"
      :timeout="state.snackbar.timeout"
      :color="state.snackbar.color"
      top
      right
      transition="slide-x-transition"
      absolute
      style="margin-right: 95px; margin-top: -2px"
    >
      {{ state.snackbar.text }}

      <v-progress-circular
              v-if="state.snackbar.loading"
              indeterminate
      ></v-progress-circular>

      <v-btn
              v-if="!state.snackbar.loading"
              text
              @click="close_snackbar_message($event)"
      >
        Close
      </v-btn>
    </v-snackbar>
    <v-fade-transition>
      <div v-show="loading" class="jd-loading-overlay"></div>
    </v-fade-transition>
  </v-app>
</template>

<script>
export default {
  methods: {
    checkNotebookContext() {
      this.notebook_context = document.getElementById("ipython-main-app")
        || document.querySelector('.jp-LabShell');
      return this.notebook_context;
    },
    getReadTheDocsLink() {
      if (['specviz', 'specviz2d', 'cubeviz', 'mosviz', 'imviz'].indexOf(this.config) !== -1) {
        return 'https://jdaviz.readthedocs.io/en/'+this.vdocs+'/'+this.config+'/index.html'
      } else {
        return 'https://jdaviz.readthedocs.io'
      }
    },
    trayItemVisible(trayItem, tray_items_filter) {
      if (tray_items_filter === null || tray_items_filter.length == 0) {
        return true
      }
      // simple exact text search match on the plugin title for now.
      return trayItem.label.toLowerCase().indexOf(tray_items_filter.toLowerCase()) !== -1
    },
    onLayoutChange() {
      /* Workaround for #1677, can be removed when bqplot/bqplot#1531 is released */
      window.dispatchEvent(new Event('resize'));
    }
  },
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
      primary: "#00617E",
      secondary: "#007DA4",
      accent: "#C75109",
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
  mounted() {
    /* Workaround for https://github.com/jupyter-widgets/ipywidgets/issues/2499, can be removed when ipywidgets 8 is
     * released */
    const jpOutputElem = this.$refs.mainapp.$el.closest('.jp-OutputArea-output');
    if (jpOutputElem) {
      jpOutputElem.classList.remove('jupyter-widgets');
    }
  }
};
</script>

<style id="web-app">
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

.cubeviz .lm_close {
  display: none !important;
}

.cubeviz .lm_close_tab {
  display: none;
}

.imviz .lm_close {
  /* hide the close button on the right to prevent closing the default viewer
     since we cannot easily discriminate between different viewers in the filter here */
  display: none !important;
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

.jdaviz-nested-toolbar {
  /* height of nested toolbar to match viewer toolbar height */
  height: 42px;
  margin-right: 4px;
}

.jdaviz-nested-toolbar .v-icon, .jdaviz-nested-toolbar img {
  /* icons from dark to (consistently) light */
  filter: invert(1) saturate(1) brightness(100);
}

.invert, .invert-if-dark.theme--dark {
    filter: invert(1) saturate(1) brightness(100);
    color: white;
}

.jdaviz-nested-toolbar .v-btn {
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
</style>
