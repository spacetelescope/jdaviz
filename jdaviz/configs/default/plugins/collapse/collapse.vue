<template>
  <v-card flat tile>
    <v-container>
      <v-row>
        <v-col class="py-0">
          <v-select
            :items="data_items"
            v-model="selected_data_item"
            label="Data"
            hint="Select the data set to use in collapse."
            persistent-hint
          ></v-select>
        </v-col>
      </v-row>
      <v-row>
        <v-col>
          <v-select
            :items="axes"
            v-model="selected_axis"
            label="Axis"
            hint="Select the axis along with the data with be collapsed."
            persistent-hint
          ></v-select>
        </v-col>
        <v-col>
          <v-select
            :items="funcs"
            v-model="selected_func"
            label="Method"
            hint="Select the method to use in the collapse."
            persistent-hint
          ></v-select>
        </v-col>
      </v-row>
    </v-container>
    <v-container v-if="selected_axis == 0">
      <v-row>
        <v-col>
          <v-select
            :items="spectral_subset_items"
            v-model="selected_subset"
            label="Spectral Region"
            hint="Optional: limit to a spectral region defined in the spectrum viewer."
            persistent-hint
            @click="list_subsets"
          ></v-select>
        </v-col>
      </v-row>
      <v-row>
        <v-col>
          <v-text-field
            label="Lower spectral bound"
            v-model="spectral_min"
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
            v-model="spectral_max"
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
      <div class="flex-grow-1"></div>
      <v-btn color="accent" text @click="collapse">Apply</v-btn>
    </v-card-actions>
  </v-card>
</template>
