<template>
  <v-app id="inspire">
    <div v-if="loadRemoteCSS()"></div>
    <g-tray-area></g-tray-area>

    <g-default-toolbar></g-default-toolbar>

    <v-content>
      <v-container class="fill-height" fluid style="padding: 0px">
        <v-row align="center" justify="center" class="fill-height">
          <v-col class="fill-height" style="padding-top: 0px; padding-bottom: 0px">
            <g-content-area></g-content-area>
          </v-col>
        </v-row>
      </v-container>
    </v-content>
  </v-app>
</template>
