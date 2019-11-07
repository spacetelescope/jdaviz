<template>
  <v-content>
    <v-container fluid
                 class="fill-height"
    >
      <v-col cols="12">
      <v-row v-if="top_area"
             class="fill-height"
      >
        <v-col cols="12"
        >
          <g-tab-area-top></g-tab-area-top>
        </v-col>
      </v-row>
      <v-row v-if="bottom_area"
             class="fill-height"
      >
        <v-col cols="12"
        >
          <g-tab-area-bottom></g-tab-area-bottom>
        </v-col>
      </v-row>
      </v-col>
    </v-container>
  </v-content>
</template>
