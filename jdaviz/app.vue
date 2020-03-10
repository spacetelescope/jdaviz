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
                <splitpanes
                  @resize="relayout"
                  @pane-add="relayout"
                  @pane-click="console.log('OMG IT WORKS')"
                >
                  <pane v-for="(stack, index) in stack_items" :key="index">
                    <v-card class="ma-2" tile style="height: calc(100% - 16px)">
                      <v-tabs
                        v-model="stack.tab"
                        :height="settings.show_tab_headers ? '36px' : '0px'"
                        :background-color="selected_stack_item.id == stack.id ? 'accent' : 'secondary'"
                        style="height: 100%"
                      >
                        <!-- style="height: calc(100% - 36px)" -->
                        <draggable
                          v-model="stack.viewers"
                          :group="{name: 'viewers'}"
                          class="d-flex flex-grow-1"
                        >
                          <v-tab
                            v-for="viewer in stack.viewers"
                            :key="viewer.id"
                            @click="selected_stack_item = stack; selected_viewer_item = viewer"
                          >
                            {{ viewer.title }}
                            {{ selected_stack_item.id == stack.id }}
                            <v-spacer></v-spacer>
                            <v-btn
                              icon
                              x-small
                              @click.stop="remove_viewer([viewer.id, stack.id])"
                              style="margin-left: 10px"
                            >
                              <v-icon>mdi-close</v-icon>
                            </v-btn>
                          </v-tab>
                        </draggable>

                        <v-btn icon tile @click.stop="split_pane('horizontal')">
                          <v-icon>mdi-view-split-horizontal</v-icon>
                        </v-btn>

                        <v-btn icon tile @click.stop="split_pane('vertical')">
                          <v-icon>mdi-view-split-vertical</v-icon>
                        </v-btn>

                        <v-tabs-items v-model="stack.tab" style="height: calc(100% - 36px)">
                          <v-tab-item
                            v-for="viewer in stack.viewers"
                            :key="viewer.id"
                            transition="false"
                            reverse-transition="false"
                            class="fill-height pa-2"
                            style="height: calc(100% + 36px)"
                          >
                            <v-toolbar
                              dense
                              floating
                              absolute
                              right
                              class="mt-2 float-right"
                              elevation="1"
                            >
                              <jupyter-widget
                                :widget="viewer.tools"
                                :key="index"
                                class="float-right"
                              />
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
                              </v-btn-toggle>
                            </v-speed-dial>-->
                            <jupyter-widget
                              :widget="viewer.widget"
                              style="width: 100%; height: 100%"
                            />
                          </v-tab-item>
                        </v-tabs-items>
                      </v-tabs>
                    </v-card>
                  </pane>
                </splitpanes>
              </pane>
              <pane size="20">
                <splitpanes horizontal class="elevation-2">
                  <pane>
                    <v-tabs grow height="36px" style="height: 100%">
                      <v-tab>Data</v-tab>

                      <v-tab-item class="overflow-y-auto" style="height: calc(100% - 36px)">
                          <v-treeview
                            dense
                            selectable
                            :items="data_items"
                            v-model="selected_data_items"
                            hoverable
                            activatable
                            item-disabled="locked"
                            @update:active="console.log($event)"
                            @input="data_item_selected"
                          ></v-treeview>
                          <!-- v-model="((stack_items.find(x => x.id == self.selected_stack_item_id) || { viewers: [] }).viewers.find(x => x.id == self.selected_viewer_item_id) || { selected_data_items: []}).selected_data_items" -->
                      </v-tab-item>
                    </v-tabs>
                  </pane>
                  <pane>
                    <v-tabs grow height="36px" style="height: 100%">
                      <v-tab>Layer Options</v-tab>
                      <v-tab>Viewer Options</v-tab>

                      <v-tab-item eager class="overflow-y-auto" style="height: 100%">
                        <!-- <v-card
                          v-if="selected_viewer_item != undefined"
                          flat
                          class="overflow-y-auto"
                          style="height: 100%"
                        >-->
                        <jupyter-widget
                          v-if="selected_viewer_item != undefined"
                          :widget="selected_viewer_item.layer_options"
                        />
                        <!-- </v-card> -->
                      </v-tab-item>
                      <v-tab-item eager class="overflow-y-auto" style="height: 100%">
                        <!-- <v-card
                          v-if="selected_viewer_item != undefined"
                          flat
                          class="overflow-y-auto"
                          style="height: 100%"
                        >-->
                        <jupyter-widget
                          v-if="selected_viewer_item != undefined"
                          :widget="selected_viewer_item.viewer_options"
                        />
                        <!-- </v-card> -->
                      </v-tab-item>
                    </v-tabs>
                  </pane>
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

/* .splitpanes__splitter {
    background-color: #ccc;
    position: relative;
}
.splitpanes__splitter:before {
    content: '';
    position: absolute;
    left: 0;
    top: 0;
    transition: opacity 0.4s;
    background-color: rgba(255, 0, 0, 0.3);
    opacity: 0;
    z-index: 1;
}

.splitpanes--vertical > .splitpanes__splitter:before {
    left: -10px;
    right: -10px;
    height: 100%;
}

.splitpanes--horizontal > .splitpanes__splitter:before {
    top: -10px;
    bottom: -10px;
    width: 100%;
} */
</style>
