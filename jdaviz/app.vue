<template>
  <v-app id="web-app">
    <div v-if="loadRemoteCSS()"></div>

    <splitpanes style="min-height: 500px">
      <pane v-if="!checkNotebookContext()" size="20" max-size="25" min-size="15">
        <g-tray-area></g-tray-area>
      </pane>
      <pane>
        <g-default-toolbar></g-default-toolbar>
        <g-viewer-area></g-viewer-area>
      </pane>
    </splitpanes>
  </v-app>
</template>
