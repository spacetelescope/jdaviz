<template>
  <v-card flat tile>
    <!-- <v-divider></v-divider> -->

    <v-card-actions>
      <div class="flex-grow-1"></div>
      <v-btn
      color="primary" text @click="slit_overlay">Apply</v-btn>
    </v-card-actions>

    <v-card-actions>
      <div class="flex-grow-1"></div>
      <v-btn
      color="primary" text @click="slit_overlay_remove">Remove</v-btn>
    </v-card-actions>

  </v-card>
</template>
