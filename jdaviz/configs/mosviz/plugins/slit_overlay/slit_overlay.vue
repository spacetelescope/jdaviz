<template>
  <v-card flat tile>
    <!-- <v-divider></v-divider> -->

    <v-card-actions>
      <div class="flex-grow-1">
        <v-row align="center" justify="center">
          <v-checkbox v-model="visible" label="Visible" @click.native="change_visible"></v-checkbox>
        </v-row>
      </div>
    </v-card-actions>

  </v-card>
</template>
