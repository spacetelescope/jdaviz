<template>
    <j-tray-plugin>
      <v-row>
        <j-docs-link :link="'https://jdaviz.readthedocs.io/en/'+vdocs+'/'+config+'/plugins.html#gaussian-smooth'">Smooth your data in xy or wavelength with a Gaussian kernel</j-docs-link>
      </v-row>

      <v-row>
        <v-select
          :items="dc_items"
          v-model="selected_data"
          label="Data"
          hint="Select the data set to be smoothed."
          persistent-hint
        ></v-select>
      </v-row>

      <v-row v-if="show_modes">
        <v-select
          :items="smooth_modes"
          v-model="selected_mode"
          label="Smoothing Type"
          hint="Smooth data spectrally or spatially."
          persistent-hint
        ></v-select>
      </v-row>

      <v-row>
        <v-text-field
          ref="stddev"
          label="Standard deviation"
          v-model="stddev"
          type="number"
          hint="The stddev of the kernel, in pixels."
          persistent-hint
          :rules="[() => !!stddev || 'This field is required', () => stddev > 0 || 'Kernel must be greater than zero']"
        ></v-text-field>
      </v-row>

      <v-row v-if="selected_data && stddev > 0">
        <v-select v-if="selected_mode == 'Spatial'"
          :items="viewers"
          v-model="selected_viewer"
          label='Plot in Viewer'
          hint='Smoothed data will replace plot in the specified viewer.  Will also be available in the data dropdown in all image viewers.'
          persistent-hint></v-select>
        <v-switch v-if="selected_mode == 'Spectral'"
          label="Plot in Viewer"
          hint="Smoothed data will immediately plot in the spectral viewer.  Will also be available in the data menu of each viewer."
          v-model="add_replace_results"
          persistent-hint>
        </v-switch>
      </v-row>

      <v-row justify="end">
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
      </v-row>
    </j-tray-plugin>
</template>
