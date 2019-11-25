<template>
  <v-app id="inspire">
    <div v-if="loadRemoteCSS()"></div>
    <div v-if="!checkNotebookContext()">
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
    </div>
    <div v-else>
      <g-toolbar>
        <template v-if="show_tray_bar">
          <v-app-bar-nav-icon @click.stop="drawer = !drawer" tile style="margin-left: -16px" />
          <v-divider vertical></v-divider>
        </template>
      </g-toolbar>
      <v-container class="py-0">
        <v-row>
            <g-tray-bar />
            <g-content-area />
        </v-row>
      </v-container>
    </div>
  </v-app>
</template>
