<template>
  <v-tabs
          v-model="tab"
          background-color="indigo"
          dark
  >
    <v-tabs-slider></v-tabs-slider>

      <v-tab href="#tab-1">
        Recents
      </v-tab>

      <v-tab href="#tab-2">
        Favorites
      </v-tab>

      <v-tab href="#tab-3">
        Nearby
      </v-tab>
  </v-tabs>

  <v-tabs-items v-model="tab">
    <v-tab-item
            v-for="i in 3"
            :key="i"
            :value="'tab-' + i"
    >
      <v-card flat>
        <v-card-text>{{ text }}</v-card-text>
      </v-card>
    </v-tab-item>
  </v-tabs-items>
</template>
