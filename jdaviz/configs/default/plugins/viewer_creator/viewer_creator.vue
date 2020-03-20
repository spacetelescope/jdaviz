<template>
  <v-menu offset-y>
    <template v-slot:activator="{ on: menu }">
      <!-- <v-tooltip> -->
        <!-- <template v-slot:activator="{ on: tooltip }"> -->
          <v-btn icon tile v-on="{...menu}">
            <v-icon>mdi-chart-histogram</v-icon>
          </v-btn>
        <!-- </template> -->
        <!-- <span>Viewers</span> -->
      <!-- </v-tooltip> -->
    </template>
    <v-list>
      <v-list-item v-for="(viewer, i) in viewer_types" @click="create_viewer(viewer.name)">
        <v-list-item-content>{{ viewer.label }}</v-list-item-content>
      </v-list-item>
    </v-list>
  </v-menu>
</template>
