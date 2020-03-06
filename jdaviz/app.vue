<template>
  <v-app id="web-app">
    <div v-if="loadRemoteCSS()"></div>

    <v-app-bar dark color="primary" flat dense app absolute height="49px" clipped-right>
      <v-toolbar-items>
        <jupyter-widget :widget="item.widget" v-for="item in tool_items" :key="item.name"></jupyter-widget>
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

    <v-content>
      <v-container class="fill-height pa-0" fluid>
        <v-row align="center" justify="center" class="fill-height pa-0 ma-0" style="width: 100%">
          <v-col cols="12" class="fill-height pa-0 ma-0" style="width: 100%">
            <splitpanes>
              <pane size="80">
                <splitpanes @resize="relayout" @pane-click="console.log($event)">
                  <pane v-for="(stack, index) in stack_items" :key="index">
                    <v-tabs
                      v-model="stack.tab"
                      height="36px"
                      :background-color="selected_stack_item_id == stack.id ? 'accent' : ''"
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
                          @click="selected_stack_item_id = stack.id; selected_viewer_item = viewer"
                        >
                          {{ viewer.title }}
                          {{ selected_stack_item_id == stack.id }}
                          <v-spacer></v-spacer>
                          <v-btn
                            icon
                            x-small
                            @click.stop="close_tab(viewer.id)"
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

                      <v-tabs-items v-model="stack.tab" class="fill-height">
                        <v-tab-item
                          v-for="viewer in stack.viewers"
                          :key="viewer.id"
                          transition="false"
                          reverse-transition="false"
                          class="fill-height pa-2"
                        >
                          <!-- <v-toolbar dense floating style="float: right">
                        <v-text-field hide-details prepend-icon="search" single-line></v-text-field>

                        <v-btn icon>
                          <v-icon>my_location</v-icon>
                        </v-btn>

                        <v-btn icon>
                          <v-icon>mdi-dots-vertical</v-icon>
                        </v-btn>
                          </v-toolbar>-->

                          <!-- <v-speed-dial v-model="viewer.fab" direction="right" fixed open-on-hover>
                        <template v-slot:activator>
                          <v-btn v-model="viewer.fab" color="blue darken-2" dark small fab>
                            <v-icon v-if="viewer.fab">mdi-close</v-icon>
                            <v-icon v-else>mdi-account-circle</v-icon>
                          </v-btn>
                        </template>
                        <v-btn fab dark small color="green">
                          <v-icon>mdi-pencil</v-icon>
                        </v-btn>
                        <v-btn fab dark small color="indigo">
                          <v-icon>mdi-plus</v-icon>
                        </v-btn>
                        <v-btn fab dark small color="red" @click="(e) => { drawer_item = viewer; drawer = !drawer }">
                          <v-icon>mdi-delete</v-icon>
                          </v-btn>-->
                          <!-- <v-menu offset-y :close-on-content-click="false" left>
                          <template v-slot:activator="{ on }">
                            <v-btn fab dark small v-on="on" color="pink">
                              <v-icon>mdi-settings</v-icon>
                            </v-btn>
                          </template>
                          <v-tabs grow height="36px" style="height: 100%">
                            <v-tab>Data</v-tab>
                            <v-tab>Layer</v-tab>
                            <v-tab>Viewer</v-tab>

                            <v-tab-item class="overflow-y-auto" style="height: 100%">
                              <v-treeview
                                dense
                                selectable
                                :items="data_items"
                                v-model="selected_data_items"
                                hoverable
                                activatable
                              ></v-treeview>
                            </v-tab-item>
                            <v-tab-item>
                              <v-card flat class="overflow-y-auto" style="height: 100%">
                                <jupyter-widget :widget="viewer.layer_options" />
                              </v-card>
                            </v-tab-item>
                            <v-tab-item>
                              <v-card flat class="overflow-y-auto" style="height: 100%">
                                <jupyter-widget :widget="viewer.viewer_options" />
                              </v-card>
                            </v-tab-item>
                          </v-tabs>
                          </v-menu>-->
                          <!-- </v-speed-dial> -->

                          <jupyter-widget
                            :widget="viewer.widget"
                            style="width: 100%; height: 100%"
                          />
                        </v-tab-item>
                      </v-tabs-items>
                    </v-tabs>
                  </pane>
                </splitpanes>
              </pane>
              <pane size="20">
                <splitpanes horizontal>
                  <pane>
                    <v-tabs grow height="36px" style="height: 100%">
                      <v-tab>Data</v-tab>

                      <v-tab-item class="overflow-y-auto" style="height: 100%">
                        <v-treeview
                          dense
                          selectable
                          :items="data_items"
                          v-model="selected_viewer_item.selected_data_items"
                          hoverable
                          activatable
                          item-disabled="locked"
                        ></v-treeview>
                      </v-tab-item>
                    </v-tabs>
                  </pane>
                  <pane>
                    <v-tabs grow height="36px" style="height: 100%">
                      <v-tab>Layer Options</v-tab>
                      <v-tab>Viewer Options</v-tab>

                      <v-tab-item>
                        <v-card flat class="overflow-y-auto" style="height: 100%">
                          <jupyter-widget :widget="selected_viewer_item.layer_options" />
                        </v-card>
                      </v-tab-item>
                      <v-tab-item>
                        <v-card flat class="overflow-y-auto" style="height: 100%">
                          <jupyter-widget :widget="selected_viewer_item.viewer_options" />
                        </v-card>
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
/* .v-toolbar__content {
    padding-left: 0px;
    padding-right: 0px;
} */

.splitpanes__splitter {
  background-color: #ccc;
  position: relative;
}
.splitpanes__splitter:before {
  content: "";
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
}

.v-toolbar__content::before {
  border-bottom: 1px solid #ccc;
}

.v-treeview > .v-treeview-node--leaf {
  margin-left: 0px;
  padding-left: 0px;
}

.v-treeview > .v-treeview-node--leaf > .v-treeview-node__root {
  padding-left: 16px;
}

.glComponent {
  width: 100%;
  height: 100%;
  overflow: auto;
}
</style>
