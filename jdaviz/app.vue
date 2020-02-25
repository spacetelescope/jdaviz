<template>
  <v-app id="web-app">
    <div v-if="loadRemoteCSS()"></div>

    <v-navigation-drawer v-model="drawer" app>
      <v-list dense>
        <v-list-item link>
          <v-list-item-action>
            <v-icon>mdi-home</v-icon>
          </v-list-item-action>
          <v-list-item-content>
            <v-list-item-title>Home</v-list-item-title>
          </v-list-item-content>
        </v-list-item>
        <v-list-item link>
          <v-list-item-action>
            <v-icon>mdi-contact-mail</v-icon>
          </v-list-item-action>
          <v-list-item-content>
            <v-list-item-title>Contact</v-list-item-title>
          </v-list-item-content>
        </v-list-item>
      </v-list>
    </v-navigation-drawer>

    <v-app-bar flat dense app color="indigo" dark>
      <v-app-bar-nav-icon @click.stop="drawer = !drawer" />
      <v-toolbar-title>Application</v-toolbar-title>
    </v-app-bar>

    <v-content>
      <v-container class="fill-height pa-0" fluid>
        <v-row align="center" justify="center" class="fill-height pa-0 ma-0" >
          <v-col cols="12" class="fill-height pa-0 ma-0">
            <golden-layout class="fill-height">
              <gl-row>
                <gl-component title="component1" class="fill-height">
                  <h1>Component 1</h1>
                </gl-component>
                <gl-stack>
                  <gl-component title="component2" class="fill-height">
                    <h1>Component 2</h1>
                  </gl-component>
                  <gl-component title="component3" class="fill-height">
                    <h1>Component 3</h1>
                  </gl-component>
                </gl-stack>
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
        window.addEventListener('resize', function () { console.log("RESIZING"); });
        var muiIconsSheet = document.createElement('link');
        muiIconsSheet.type = 'text/css';
        muiIconsSheet.rel = 'stylesheet';
        muiIconsSheet.href = 'https://cdn.jsdelivr.net/npm/@mdi/font@4.x/css/materialdesignicons.min.css';
        document.getElementsByTagName('head')[0].appendChild(muiIconsSheet);
        return true;
    }
  }
}
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
}

.v-toolbar__content::before {
    border-bottom: 1px solid #ccc;

}

.v-treeview>.v-treeview-node--leaf {
    margin-left: 0px;
    padding-left: 0px;
}

.v-treeview>.v-treeview-node--leaf>.v-treeview-node__root {
    padding-left: 16px;
}

.glComponent {
    width: 100%;
    height: 100%;
    overflow: auto;
}
</style>
