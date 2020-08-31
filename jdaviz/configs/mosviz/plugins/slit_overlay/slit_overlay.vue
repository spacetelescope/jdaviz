<template>
  <v-card flat tile>
    <!-- <v-divider></v-divider> -->

    <v-card-actions>
      <div class="flex-grow-1">
        <v-row align="center" justify="center">
          <v-btn
            color="primary" text @click="slit_overlay">Apply</v-btn>
          <v-btn
            color="primary" text @click="slit_overlay_remove">Remove</v-btn>
        </v-row>
      </div>
    </v-card-actions>

  </v-card>
</template>
