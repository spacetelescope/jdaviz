<template>
  <v-card flat tile>
    <v-container>
      <v-row>
        <v-col class="py-0">
          <v-select
            :items="dc_items"
            v-model="selected_data"
            label="Data"
            hint="Select the data set."
            persistent-hint
          ></v-select>
        </v-col>
      </v-row>
      <v-row>
      </v-row>
    </v-container>
    <!-- <v-divider></v-divider> -->

    <v-card-actions>
    </v-card-actions>
  </v-card>
</template>
