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
        <v-col>
          <v-text-field
            ref="n_moment"
            label="Moment"
            v-model="n_moment"
            type="number"
            hint="The desired moment."
            persistent-hint
            :rules="[() => !!n_moment || 'This field is required', () => n_moment >= 0 || 'Moment must be zero or a positive integer']"
          ></v-text-field>
        </v-col>
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
      </v-row>
    </v-container>
    <!-- <v-divider></v-divider> -->

    <v-card-actions>
      <v-btn color="primary" text @click="calculate_moment">Calculate</v-btn>
    </v-card-actions>
  </v-card>
</template>
