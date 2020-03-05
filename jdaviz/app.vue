<template>
  <v-app id="web-app">
    <div v-if="loadRemoteCSS()"></div>

    <v-app-bar flat dense app color="indigo" dark>
      <v-toolbar-items>
        <jupyter-widget :widget="tool.widget" v-for="tool in tools" :key="tool.name"></jupyter-widget>
      </v-toolbar-items>
    </v-app-bar>

    <v-content>
      <v-container class="fill-height pa-0" fluid>
        <v-row align="center" justify="center" class="fill-height pa-0 ma-0" style="width: 100%">
          <v-col cols="12" class="fill-height pa-0 ma-0" style="width: 100%">
            <golden-layout class="fill-height" style="width: 100%">
              <gl-row>
                <gl-col width="15" v-if="show_tray_bar">
                  <gl-stack>
                    <gl-component title="Data">

                    </gl-component>
                  </gl-stack>
                </gl-col>
                <gl-row width="80">
                  <component
                    v-for="(view, index) in viewer_layout"
                    v-bind:is="view.type"
                    v-bind:key="view.name"
                  >
                    <gl-component :title="view.name" class="pa-2">
                      <v-speed-dial
                              v-model="view.fab"
                              fixed
                              direction="right"
                      >
                        <template v-slot:activator>
                          <v-btn
                                  v-model="view.fab"
                                  color="blue darken-2"
                                  dark
                                  small
                                  fab
                          >
                            <v-icon v-if="view.fab">mdi-close</v-icon>
                            <v-icon v-else>mdi-account-circle</v-icon>
                          </v-btn>
                        </template>
                        <v-btn
                                fab
                                dark
                                small
                                color="green"
                        >
                          <v-icon>mdi-pencil</v-icon>
                        </v-btn>
                        <v-btn
                                fab
                                dark
                                small
                                color="indigo"
                        >
                          <v-icon>mdi-plus</v-icon>
                        </v-btn>
                        <v-btn
                                fab
                                dark
                                small
                                color="red"
                        >
                          <v-icon>mdi-delete</v-icon>
                        </v-btn>
                      </v-speed-dial>
                      <jupyter-widget :widget="view.widget"></jupyter-widget>
                    </gl-component>

                  </component>
                </gl-row>
              </gl-row>
            </golden-layout>
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
