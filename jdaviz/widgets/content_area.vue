<template>
  <v-content>
    <v-container
      fluid
      class="fill-height py-0"
    >
      <v-row
        v-if="top_area"
        align="center"
        justify="center"
        class="fill-height">
        <v-col
          class="center fill-height pa-0">
          <g-tab-area-top></g-tab-area-top>
        </v-col>
      </v-row>
      <v-row
        v-if="bottom_area"
        align="center"
        justify="center"
        class="fill-height">
        <v-col
          class="center fill-height pa-0">
          <g-tab-area-bottom></g-tab-area-bottom>
        </v-col>
      </v-row>
    </v-container>
  </v-content>
</template>
