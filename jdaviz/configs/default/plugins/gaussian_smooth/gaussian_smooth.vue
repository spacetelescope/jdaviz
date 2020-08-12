<template>
  <v-card flat tile>
    <v-container>
      <v-row>
        <v-col class="py-0">
          <v-select
            :items="dc_items"
            v-model="selected_data"
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
            type="number"
            hint="The stddev of the kernel, in pixels."
            persistent-hint
            :rules="[() => !!stddev || 'This field is required', () => stddev > 0 || 'Kernel must be greater than zero']"
          ></v-text-field>
        </v-col>
      </v-row>
    </v-container>
    <!-- <v-divider></v-divider> -->

    <v-card-actions>
      <div class="flex-grow-1"></div>
      <v-btn :disabled="stddev <= 0 || selected_data == ''"
      color="accent" text @click="gaussian_smooth">Apply</v-btn>
    </v-card-actions>
  </v-card>
</template>
