<template>
  <v-app id="web-app">
    <div v-if="loadRemoteCSS()"></div>

    <template v-if="!checkNotebookContext()">
      <g-tray-area></g-tray-area>
    </template>

    <g-default-toolbar></g-default-toolbar>

    <v-content style="min-height: 500px;">
      <v-container class="fill-height" fluid style="padding: 0px; width:100%">
        <v-row align="center" justify="center" class="fill-height" style="width: 100%">
          <v-col class="fill-height" style="padding-top: 0px; padding-bottom: 0px">
            <g-viewer-area></g-viewer-area>
          </v-col>
        </v-row>
      </v-container>
    </v-content>
  </v-app>
</template>
