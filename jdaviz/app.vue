<template>
  <v-app :style="{'height=500px': checkNotebookContext()}"
  >
    <div v-if="loadRemoteCSS()"></div>
    <g-tray-bar />

    <g-toolbar>
      <template v-if="show_tray_bar">
        <v-app-bar-nav-icon @click.stop="drawer = !drawer" tile style="margin-left: -16px" />
        <v-divider vertical></v-divider>
      </template>
    </g-toolbar>

    <g-content-area />
    <v-footer
      app
    >
    </v-footer>
  </v-app>
</template>
