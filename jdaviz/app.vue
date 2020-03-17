<template>
  <v-app id="web-app">
    <div v-if="loadRemoteCSS()" v-once></div>

    <v-app-bar color="white" class="elevation-1" dense app absolute clipped-right>
      <v-toolbar-items>
        <jupyter-widget :widget="item.widget" v-for="item in tool_items" :key="item.name"></jupyter-widget>
        <v-tooltip bottom>
          <template v-slot:activator="{ on }">
            <v-btn disabled v-on="on" icon tile>
              <v-icon>mdi-format-superscript</v-icon>
            </v-btn>
          </template>
          <span>Arithmetic Editor</span>
        </v-tooltip>
        <v-tooltip bottom>
          <template v-slot:activator="{ on }">
            <v-btn disabled v-on="on" icon tile>
              <v-icon>mdi-export</v-icon>
            </v-btn>
          </template>
          <span>Export Data</span>
        </v-tooltip>

        <v-tooltip bottom>
          <template v-slot:activator="{ on }">
            <v-btn disabled v-on="on" icon tile>
              <v-icon>mdi-delete</v-icon>
            </v-btn>
          </template>
          <span>Delete Data</span>
        </v-tooltip>
      </v-toolbar-items>
      <v-divider vertical />
      <v-toolbar-items>
        <v-btn-toggle borderless tile background-color="rgba(0, 0, 0, 0)">
          <v-btn icon disabled>
            <v-icon>mdi-hand-right</v-icon>
          </v-btn>

          <v-btn icon disabled>
            <v-icon>mdi-magnify-plus</v-icon>
          </v-btn>

          <v-btn icon disabled>
            <v-icon>mdi-magnify-minus</v-icon>
          </v-btn>
        </v-btn-toggle>
      </v-toolbar-items>
      <v-divider vertical />
      <v-toolbar-items>
        <v-btn-toggle borderless tile background-color="rgba(0, 0, 0, 0)">
          <v-btn icon disabled>
            <v-icon>mdi-hand-right</v-icon>
          </v-btn>

          <v-btn icon disabled>
            <v-icon>mdi-magnify-plus</v-icon>
          </v-btn>

          <v-btn icon disabled>
            <v-icon>mdi-magnify-minus</v-icon>
          </v-btn>
        </v-btn-toggle>
      </v-toolbar-items>
      <v-divider vertical />
    </v-app-bar>

    <v-content :style="checkNotebookContext() ? 'height: 500px;' : ''">
      <v-container class="fill-height pa-0" fluid>
        <v-row align="center" justify="center" class="fill-height pa-0 ma-0" style="width: 100%">
          <v-col cols="12" class="fill-height pa-0 ma-0" style="width: 100%">
            <splitpanes class="default-theme" @resize="relayout">
              <pane size="80">
                <!-- <splitpanes
                  @resize="relayout"
                  @pane-add="relayout"
                  @pane-click="console.log('OMG IT WORKS')"
                >-->
                <!-- <pane v-for="(stack, index) in stack_items" :key="index"> -->
                <v-card tile class="ma-2" style="height: calc(100% - 16px)">
                  <golden-layout
                    style="height: 100%"
                    @selection-changed="consle.log($event)"
                    :has-headers="settings.show_tab_headers"
                  >
                    <gl-row @selection-changed="consle.log($event)" :closable="false">
                      <gl-stack
                        v-for="(stack, index) in stack_items"
                        :key="index"
                        @selection-changed="consle.log($event)"
                        :show-maximise-icon="false"
                      >
                        <gl-component
                          v-for="(viewer, index) in stack.viewers"
                          :key="index"
                          title="Test"
                          @resize="relayout"
                        >
                          <v-card tile flat style="height: calc(100% - 0px)">
                            <!-- <v-toolbar
                              dense
                              floating
                              absolute
                              right
                              class="mt-2 float-right"
                              elevation="1"
                            >
                              <v-toolbar-items>
                              <!-- <jupyter-widget
                                v-for="(tool, index) in viewer.tools"
                                :widget="tool"
                                :key="index"
                                class="float-right"
                              />-->
                              <v-menu offset-y>
                                <template v-slot:activator="{ on }">
                                  <v-btn color="primary" dark v-on="on">
                                    <v-icon>mdi-settings</v-icon>
                                  </v-btn>
                                </template>

                                <v-tabs grow height="36px" style="height: 100%">
                                  <v-tab>Data</v-tab>
                                  <v-tab>Layer</v-tab>
                                  <v-tab>Viewer</v-tab>

                                  <v-tab-item
                                    class="overflow-y-auto"
                                    style="height: calc(100% - 36px)"
                                  >
                                    <v-treeview
                                      dense
                                      selectable
                                      :items="data_items"
                                      v-model="viewer.selected_data_items"
                                      hoverable
                                      activatable
                                      item-disabled="locked"
                                      @update:active="console.log($event)"
                                      @input="data_item_selected"
                                    ></v-treeview>
                                    <!-- v-model="((stack_items.find(x => x.id == self.selected_stack_item_id) || { viewers: [] }).viewers.find(x => x.id == self.selected_viewer_item_id) || { selected_data_items: []}).selected_data_items" -->
                                  </v-tab-item>

                                  <v-tab-item eager class="overflow-y-auto" style="height: 100%">
                                    <jupyter-widget
                                      v-if="selected_viewer_item != undefined"
                                      :widget="viewer.layer_options"
                                    />
                                  </v-tab-item>

                                  <v-tab-item eager class="overflow-y-auto" style="height: 100%">
                                    <jupyter-widget
                                      v-if="selected_viewer_item != undefined"
                                      :widget="viewer.viewer_options"
                                    />
                                  </v-tab-item>
                                </v-tabs>
                              </v-menu>
                            </v-toolbar-items>
                          </v-toolbar>

                          <!-- <v-speed-dial v-model="viewer.fab" direction="left" right absolute>
                              <template v-slot:activator>
                                <v-btn
                                  v-model="viewer.fab"
                                  color="blue darken-2"
                                  dark
                                  small
                                  fab
                                  class="elevation-0"
                                >
                                  <v-icon v-if="viewer.fab">mdi-close</v-icon>
                                  <v-icon v-else>mdi-account-circle</v-icon>
                                </v-btn>
                              </template>
                              <v-btn-toggle >
                                <jupyter-widget
                                  v-for="(tool,index) in viewer.tools"
                                  :widget="viewer.tools"
                                  :key="index"
                                />
                                  </v-tab-item>
                                </v-tabs>
                              </v-menu>
                            </v-speed-dial>
                            <jupyter-widget
                              :widget="viewer.widget"
                              style="width: 100%; height: 100%"
                            />
                          </v-card>
                        </gl-component>
                      </gl-stack>
                    </gl-row>
                  </golden-layout>
                <!-- </pane>
                </splitpanes>-->
              </pane>
              <pane size="20">
                <splitpanes horizontal class="elevation-2">
                  <pane></pane>
                </splitpanes>
              </pane>
            </splitpanes>
          </v-col>
        </v-row>
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
    },

    loadRemoteCSS() {
      window.addEventListener("resize", function() {
        console.log("RESIZING");
      });
      var muiIconsSheet = document.createElement("link");
      muiIconsSheet.type = "text/css";
      muiIconsSheet.rel = "stylesheet";
      muiIconsSheet.href =
        "https://cdn.jsdelivr.net/npm/@mdi/font@4.x/css/materialdesignicons.min.css";
      document.getElementsByTagName("head")[0].appendChild(muiIconsSheet);
      return true;
    }
  }
};
</script>

<style id="web-app">
.v-toolbar__content {
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
  background: #ffffff;
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

.splitpanes--horizontal > .splitpanes__splitter:before {
    top: -10px;
    bottom: -10px;
    width: 100%;
} */
</style>
