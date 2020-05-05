<template>
  <v-card flat tile>
    <v-container>
      <v-row>
        <v-col class="py-0">
          <v-select
            :items="dc_items"
            @change="data_selected"
            label="Data"
            hint="Select the data set to be smoothed."
            persistent-hint
          ></v-select>
        </v-col>
      </v-row>
      <v-row>
        <v-col>
          <v-text-field
            ref="stddev"
            label="Standard deviation"
            v-model="stddev"
            hint="The stddev of the kernel, in pixels."
            persistent-hint
            :rules="[() => !!stddev || 'This field is required']"
            persistent-hint
          ></v-text-field>
        </v-col>
      </v-row>
    </v-container>
    <!-- <v-divider></v-divider> -->

    <v-card-actions>
      <div class="flex-grow-1"></div>
      <v-btn color="primary" text @click="gaussian_smooth">Apply</v-btn>
    </v-card-actions>
  </v-card>
</template>
