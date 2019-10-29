<template>
  <v-content>
    <v-container
            fluid
    >
      <v-row style="height: 100%"
             v-if="top_area"
      >
        <v-col
                class="fill-height"
                cols="12"
        >
          <g-tab-area-top></g-tab-area-top>
        </v-col>
      </v-row>
      <v-row style="height: 100%"
             v-if="bottom_area"
      >
        <v-col
                class="fill-height"
                cols="12"
        >
          <g-tab-area-bottom></g-tab-area-bottom>
        </v-col>
      </v-row>
    </v-container>
  </v-content>
</template>
