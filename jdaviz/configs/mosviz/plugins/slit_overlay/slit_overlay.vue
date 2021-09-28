<template>
  <v-card flat tile>
    <!-- <v-divider></v-divider> -->

    <v-card-actions>
      <div class="flex-grow-1">
        <v-row align="center" justify="center">
          <j-tooltip tipid='plugin-slit-overlay-visible'>
            <v-checkbox v-model="visible" label="Visible" @click.native="change_visible"></v-checkbox>
          </j-tooltip>
        </v-row>
      </div>
    </v-card-actions>

  </v-card>
</template>
