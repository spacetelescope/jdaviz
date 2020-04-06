<template>
  <v-app id="web-app">
    <v-app-bar color="white" class="elevation-1" dense app absolute clipped-right>
      <!-- <v-toolbar-items> -->
      <jupyter-widget :widget="item.widget" v-for="item in state.tool_items" :key="item.name"></jupyter-widget>
      <!-- </v-toolbar-items> -->
      <v-spacer></v-spacer>
      <!-- <v-divider vertical></v-divider> -->
      <v-toolbar-items>
        <v-btn icon @click="state.drawer = !state.drawer">
          <v-icon v-if="state.drawer">mdi-toy-brick-remove</v-icon>
          <v-icon v-else>mdi-toy-brick-plus</v-icon>
        </v-btn>
      </v-toolbar-items>
    </v-app-bar>

    <v-content
      :style="checkNotebookContext() ? 'height: ' + state.settings.context.notebook.max_height : ''"
    >
      <v-container class="fill-height pa-0" fluid>
        <!-- <v-row align="center" justify="center" class="fill-height pa-0 ma-0" style="width: 100%">
        <v-col cols="12" class="fill-height pa-0 ma-0" style="width: 100%"> -->
        <splitpanes class="default-theme" @resize="relayout">
          <pane size="80">
            <v-card tile class="ma-2" style="height: calc(100% - 16px)">
              <golden-layout
                @stateChanged="consle.log($event)"
                :style="checkNotebookContext() ? 'height: 100%;' : 'height: calc(100vh - 64px)'"
                @selection-changed="consle.log($event)"
                :has-headers="state.settings.visible.tab_headers"
              >
                <gl-row :closable="false">
                  <g-viewer-tab
                    v-for="(stack, index) in state.stack_items"
                    :stack="stack"
                    :key="index"
                    :data-items="state.data_items"
                    @resize="relayout"
                    @destroy="remove_component"
                    @data-item-selected="data_item_selected($event)"
                  ></g-viewer-tab>
                </gl-row>
              </golden-layout>
            </v-card>
          </pane>
          <pane size="20" v-if="state.drawer">
            <splitpanes horizontal class="elevation-2">
              <pane>
                <v-card tile class="ma-2" style="height: calc(100% - 16px)">
                  <golden-layout
                    :style="checkNotebookContext() ? 'height: 100%;' : 'height: calc(100vh - 64px)'"
                  >
                    <gl-stack
                      @stateChanged="consle.log($event)"
                      @selection-changed="consle.log($event)"
                      :closable="false"
                    >
                      <gl-component
                        v-for="(tray, index) in state.tray_items"
                        :key="index"
                        :title="tray.name"
                      >
                        <jupyter-widget :widget="tray.widget"></jupyter-widget>
                      </gl-component>
                    </gl-stack>
                  </golden-layout>
                </v-card>
              </pane>
            </splitpanes>
          </pane>
        </splitpanes>
        <!-- </v-col>
        </v-row> -->
      </v-container>
    </v-content>
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

.splitpanes__splitter {
  box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.2), 0 2px 5px 0 rgba(0, 0, 0, 0.19);
}

.lm_goldenlayout {
  background: #fafafa;
}

.lm_content {
  background: #ffffff;
  border: none;
  border-top: 1px solid #cccccc;
}

.lm_splitter {
  background: #999999;
  opacity: 0.25;
  z-index: 1;
  transition: opacity 200ms ease;
}

.lm_header .lm_tab {
  padding-top: 0px;
  margin-top: 0px;
}

.vuetify-styles .lm_header ul {
  padding-left: 0;
}
</style>
