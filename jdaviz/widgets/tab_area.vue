<template>
  <v-card flat tile class="fill-height" style="height: 100%">
    <v-tabs
            v-model="tab"
            background-color="secondary"
            dark
    >
      <v-tabs-slider></v-tabs-slider>

      <v-tab
              v-for="(viewer, i) in active_viewers"
              :href="'#tab-' + i"
      >
        {{ viewer.name }}
      </v-tab>
    </v-tabs>

    <v-tabs-items v-model="tab">
      <v-tab-item
              v-for="(viewer, i) in active_viewers"
              :key="i"
              :value="'tab-' + i"
              transition="false"
              reverse-transition="false"
      >
        <component v-bind:is="viewer.binding"></component>
      </v-tab-item>
    </v-tabs-items>
  </v-card>
</template>
