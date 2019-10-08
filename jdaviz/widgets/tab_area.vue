<template>
  <v-tabs
          v-model="tab"
          background-color="indigo"
          dark
  >
    <v-tabs-slider></v-tabs-slider>
      <v-tab v-for="viewer in viewers" href="#tab-1">
        {{ viewer.name }}
      </v-tab>
  </v-tabs>

  <g-tab-items></g-tab-items>
  <v-tab-item
          v-for="(viewer, i) in viewers"
          :key="i"
          :value="'tab-' + i"
  >
    <v-card flat>
      <v-card-text>
        <component v-bind:is="viewer.name"></component>
      </v-card-text>
    </v-card>
  </v-tab-item>
</template>
