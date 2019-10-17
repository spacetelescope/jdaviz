<template>
  <v-card
          class="mx-auto"
          height="100%"
  >
    <v-tabs
            v-model="tab"
            background-color="indigo"
            dark
    >
      <v-tabs-slider></v-tabs-slider>

      <v-tab v-for="(viewer, i) in active_viewers" :href="'#tab-' + i">
        {{ viewer.name }}
      </v-tab>
    </v-tabs>

    <v-tabs-items v-model="tab" class="fill-height">
      <v-tab-item
              v-for="(viewer, i) in active_viewers"
              :key="i"
              :value="'tab-' + i"
              class="fill-height"
      >
        <component v-bind:is="viewer.binding"></component>
      </v-tab-item>
    </v-tabs-items>
  </v-card>
</template>
