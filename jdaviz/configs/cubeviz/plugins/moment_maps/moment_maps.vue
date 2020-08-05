<template>
  <v-card flat tile>
    <v-container>
      <v-row>
        <v-col>
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
        <v-col>
          <v-select
            :items="spectral_subset_items"
            v-model="selected_spectral_subset"
            label="Spectral Region"
            hint="Optional: limit to a spectral region defined in the spectrum viewer."
            persistent-hint
          ></v-select>
        </v-col>
      </v-row>
      <v-row>
        <v-col>
          <v-text-field
            label="Lower spectral bound"
            type="number"
            v-model.number="spectral_min"
            hint="Lower bound of spectral region"
            persistent-hint
          >
          </v-text-field>
        </v-col>
        <v-col cols = 2>
          <span>{{ spectral_unit }}</span>
        </v-col>
      </v-row>
      <v-row>
        <v-col>
          <v-text-field
            label="Upper spectral bound"
            type="number"
            v-model.number="spectral_max"
            hint="Lower bound of spectral region"
            persistent-hint
          >
          </v-text-field>
        </v-col>
        <v-col cols = 2>
          <span>{{ spectral_unit }}</span>
        </v-col>
      </v-row>
    </v-container>
    <!-- <v-divider></v-divider> -->

    <v-card-actions>
      <v-col>
        <v-text-field
          ref="n_moment"
          label="Moment"
          v-model.number="n_moment"
          type="number"
          hint="The desired moment."
          persistent-hint
          :rules="[() => !!n_moment || 'This field is required', () => n_moment >= 0 || 'Moment must be zero or a     positive integer']"
        ></v-text-field>
      </v-col>
      <v-col>
        <v-btn color="primary" text @click="calculate_moment">Calculate</v-btn>
      </v-col>
    </v-card-actions>
  </v-card>
</template>
