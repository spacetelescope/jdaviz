<template>
  <v-card flat tile>
    <v-container>
      <j-docs-link :link="'https://jdaviz.readthedocs.io/en/'+vdocs+'/'+config+'/plugins.html#gaussian-smooth'">Smooth your data in xy or wavelength with a Gaussian kernel</j-docs-link>
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
      <v-row v-if="show_modes">
        <v-col>
          <v-select
            :items="smooth_modes"
            v-model="selected_mode"
            label="Smoothing Type"
            hint="Smooth data spectrally or spatially."
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
      <v-row v-if="selected_data">
        <v-select v-if="selected_mode=='Spatial'"
          :items="viewers"
          v-model="selected_viewer"
          label='Replace data in viewer'
          hint='Replace contents in the specified viewer with results from this plugin.  Results will be available in the data dropdown in all image viewers.'
          persistent-hint></v-select>
        <v-switch v-else-if="selected_data_is_1d"
          label="Add to viewer"
          hint="Show results immediately by adding to the spectral viewer.  Smoothed data will be available in the data menu of each viewer."
          v-model="add_replace_results"
          persistent-hint>
        </v-switch>
        <v-switch v-else
          label="Replace data in viewer"
          hint="Show results immediately by replacing the displayed data in the respective image viewer.  Smoothed data will be available in the data menu of each viewer."
          v-model="add_replace_results"
          persistent-hint>
        </v-switch>
      </v-row>
    </v-container>
    <!-- <v-divider></v-divider> -->

    <v-card-actions>
      <div class="flex-grow-1"></div>
      <j-tooltip v-if="selected_mode=='Spectral'" tipid='plugin-gaussian-apply'>
        <v-btn :disabled="stddev <= 0 || selected_data == ''"
          color="accent" text 
          @click="spectral_smooth"
        >Apply</v-btn>
      </j-tooltip>
      <j-tooltip v-else tipid='plugin-gaussian-apply'>
        <v-btn 
          :disabled="stddev <= 0 || selected_data == ''"
          color="accent" text
          @click="spatial_convolution"
        >Apply</v-btn>
      </j-tooltip>
    </v-card-actions>
  </v-card>
</template>
