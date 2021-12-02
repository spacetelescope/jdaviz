<template>
  <v-card flat tile>
    <v-container>
      <j-docs-link :link="'https://jdaviz.readthedocs.io/en/'+vdocs+'/'+config+'/plugins.html#moment-maps'">Create a 2D image from a data cube</j-docs-link>
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
      <v-row>
        <v-select
          :items="viewers"
          v-model="selected_viewer"
          label='Plot in Viewer'
          hint='Moment map will replace plot in the specified viewer.  Will also be available in the data dropdown in all image viewers.'
          persistent-hint
        ></v-select>
      </v-row>
    </v-container>
    <!-- <v-divider></v-divider> -->

    <v-card-actions>
      <v-row>
        <v-col>
          <v-text-field
            ref="n_moment"
            label="Moment"
            v-model="n_moment"
            hint="The desired moment."
            persistent-hint
            :rules="[() => !!n_moment || 'This field is required']"
          ></v-text-field>
        </v-col>
        <v-col>
          <j-tooltip tipid='plugin-moment-maps-calculate'>
            <v-btn color="primary" text @click="calculate_moment">Calculate</v-btn>
          </j-tooltip>
        </v-col>
    </v-card-actions>
    <v-card-actions>
      <v-row v-if="moment_available">
        <v-col>
          <v-text-field
           v-model="filename"
           label="Filename"
           :rules="[() => !!filename || 'This field is required']">
          </v-text-field>
        </v-col>
        <v-col>
          <j-tooltip tipid='plugin-moment-save-fits'>
            <v-btn color="primary" text @click="save_as_fits">Save as FITS</v-btn>
          </j-tooltip>
        </v-col>
      </v-row>
    </v-card-actions>
  </v-card>
</template>
