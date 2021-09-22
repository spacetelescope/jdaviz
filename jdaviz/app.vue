<template>
  <v-app id="web-app" class="jdaviz">
    <v-app-bar color="primary" dark :dense="state.settings.dense_toolbar" flat app absolute clipped-right>
      <j-tooltip :doctips="state.doctips" :doctips="state.doctips" :tipid="item.name" v-for="item in state.tool_items">
        <jupyter-widget :widget="item.widget" :key="item.name"></jupyter-widget>
      </j-tooltip>
      <v-toolbar-items>
        <v-btn v-if="config === 'mosviz'" icon @click="state.settings.freeze_states_on_row_change = !state.settings.freeze_states_on_row_change">
          <v-icon v-if="state.settings.freeze_states_on_row_change">mdi-lock</v-icon>
          <v-icon v-else>mdi-lock-open-outline</v-icon>
        </v-btn>
      </v-toolbar-items>
      <v-spacer></v-spacer>
      <v-toolbar-items>
        <j-tooltip :doctips="state.doctips" tipid="app-toolbar-doctips">
          <v-btn icon @click="state.doctips = !state.doctips">
            <v-icon v-if="state.doctips">mdi-help-circle</v-icon>
            <v-icon v-else>mdi-help-circle-outline</v-icon>
          </v-btn>  
        </j-tooltip>
        <j-tooltip :doctips="state.doctips" tipid="app-toolbar-plugins">
          <v-btn icon @click="state.drawer = !state.drawer">
            <v-icon v-if="state.drawer">mdi-toy-brick-remove</v-icon>
            <v-icon v-else>mdi-toy-brick-plus</v-icon>
          </v-btn>
        </j-tooltip>
      </v-toolbar-items>
    </v-app-bar>

    <v-content
      :style="checkNotebookContext() ? 'height: ' + state.settings.context.notebook.max_height + '; border: solid 1px #e5e5e5;' : 'max-height: calc(100% - 48px)'"
    >
      <v-container class="fill-height pa-0" fluid>
        <splitpanes @resize="relayout">
          <pane size="75">
            <golden-layout
              style="height: 100%;"
              :has-headers="state.settings.visible.tab_headers"
            >
              <gl-row :closable="false">
                <g-viewer-tab
                  v-for="(stack, index) in state.stack_items"
                  :stack="stack"
                  :key="index"
                  :data-items="state.data_items"
                  :doctips="state.doctips"
                  @resize="relayout"
                  @destroy="destroy_viewer_item($event)"
                  @data-item-selected="data_item_selected($event)"
                  @save-figure="save_figure($event)"
                ></g-viewer-tab>
              </gl-row>
            </golden-layout>
          </pane>
          <pane size="25" v-if="state.drawer" style="background-color: #fafbfc;">
            <v-card flat tile class="overflow-y-auto fill-height" color="#f8f8f8">
              <v-expansion-panels accordion multiple focusable flat tile>
                <v-expansion-panel v-for="(tray, index) in state.tray_items" :key="index">
                  <v-expansion-panel-header>
                    <j-tooltip :doctips="state.doctips" :tipid="tray.name">
                      {{ tray.label }}
                    </j-tooltip>
                  </v-expansion-panel-header>
                  <v-expansion-panel-content>
                    <jupyter-widget :widget="tray.widget"></jupyter-widget>
                  </v-expansion-panel-content>
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
      :top=true
      absolute
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
    }
  },
  created() {
    this.$vuetify.theme.themes.light = {
      primary: "#00617E",
      secondary: "#007DA4",
      accent: "#C75109",
      error: '#FF5252',
      info: '#2196F3',
      success: '#4CAF50',
      warning: '#FFC107',
    };
    this.$vuetify.theme.themes.dark = {
      primary: "#00617E",
      secondary: "#007DA4",
      accent: "#C75109",
      error: '#FF5252',
      info: '#2196F3',
      success: '#4CAF50',
      warning: '#FFC107',
    };
  }
};
</script>

<style id="web-app">

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

.vuetify-styles .lm_header ul {
  padding-left: 0;
}

.v-expansion-panel-content__wrap {
  padding: 0px;
  margin: 0px;
}

.v-expansion-panel__header {
  padding: 0px;
  margin: 0px;
}

.vuetify-styles .v-expansion-panel-content__wrap {
  padding: 0px;
  margin: 0px;
}


/* vue-tippy (used in tooltip.vue) creates a div that defaults to block which 
  screws up any toolbar alignment.  Unfortunately no class or id are provided
  or can be passed for tooltip.vue.  However, we always set the interactive
  attribute, so can filter on that here.
  */
div[interactive] {
  display: inline-flex;
  height: inherit;
}
.col > div[interactive] {
  display: inline-block;
}

div[interactive] > div[tabindex] {
  display: inline-flex;
}

.v-tooltip__content, .tippy-backdrop, .tippy-arrow, .tippy-tooltip {
  background-color: white !important;
}  

.tippy-arrow {
  border-bottom-color: white !important
}

.v-tooltip__content, .tippy-tooltip {
  border-radius: 2px !important;
  border: 1px #c75109 solid !important;
}

.v-tooltip__content, .tippy-content {
  color: #00617e !important;
}

.tippy-content > a {
  text-decoration: underline !important;
}


</style>
