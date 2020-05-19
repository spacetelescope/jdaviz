<template>
  <v-app id="web-app">
    <v-app-bar dark dense flat app absolute clipped-right>
      <jupyter-widget :widget="item.widget" v-for="item in state.tool_items" :key="item.name"></jupyter-widget>
      <v-spacer></v-spacer>
      <v-toolbar-items>
        <v-btn icon @click="state.drawer = !state.drawer">
          <v-icon v-if="state.drawer">mdi-toy-brick-remove</v-icon>
          <v-icon v-else>mdi-toy-brick-plus</v-icon>
        </v-btn>
      </v-toolbar-items>
    </v-app-bar>

    <v-content
      :style="checkNotebookContext() ? 'height: ' + state.settings.context.notebook.max_height + '; border: solid 1px #e5e5e5;' : ''"
    >
      <v-container class="fill-height pa-0" fluid>
        <splitpanes @resize="relayout">
          <pane size="75">
              <golden-layout
                :style="checkNotebookContext() ? 'height: 100%;' : 'height: calc(100vh - 48px)'"
                :has-headers="state.settings.visible.tab_headers"
              >
                <gl-row :closable="false">
                  <g-viewer-tab
                    v-for="(stack, index) in state.stack_items"
                    :stack="stack"
                    :key="index"
                    :data-items="state.data_items"
                    @resize="relayout"
                    @destroy="destroy_viewer_item($event)"
                    @data-item-selected="data_item_selected($event)"
                  ></g-viewer-tab>
                </gl-row>
              </golden-layout>
          </pane>
          <pane size="25" v-if="state.drawer" style="background-color: #fafbfc;">
            <v-expansion-panels accordion multiple focusable flat tile>
              <v-expansion-panel v-for="(tray, index) in state.tray_items" :key="index">
                <v-expansion-panel-header>{{ tray.label }}</v-expansion-panel-header>
                <v-expansion-panel-content>
                  <jupyter-widget :widget="tray.widget"></jupyter-widget>
                </v-expansion-panel-content>
              </v-expansion-panel>

            </v-expansion-panels>
            <v-divider></v-divider>
          </pane>
        </splitpanes>
      </v-container>
    </v-content>
    <v-snackbar
            v-model="state.snackbar.show"
            :timeout="state.snackbar.timeout"
            :color="state.snackbar.color"
            absolute>
      {{ state.snackbar.text }}
      <v-btn text @click="state.snackbar = false">Close</v-btn>
    </v-snackbar>
  </v-app>
</template>

<script>
export default {
  methods: {
    checkNotebookContext() {
      this.notebook_context = document.getElementById("ipython-main-app");
      return this.notebook_context;
    }
  }
};
</script>

<style id="web-app">
  .v-toolbar__content,
  .vuetify-styles .v-toolbar__content {
    padding-left: 0px;
    padding-right: 0px;
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
    width: 1px;
  }

  .lm_goldenlayout {
    background: #ffffff;
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

  .lm_splitter.lm_vertical {
    height: 1px !important;
  }

  .lm_splitter.lm_horizontal {
    width: 1px !important;
  }

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
</style>
