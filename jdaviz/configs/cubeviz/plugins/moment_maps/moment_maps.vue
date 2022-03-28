<template>
  <j-tray-plugin>
    <v-row>
      <j-docs-link :link="'https://jdaviz.readthedocs.io/en/'+vdocs+'/'+config+'/plugins.html#moment-maps'">Create a 2D image from a data cube</j-docs-link>
    </v-row>

    <v-row>
      <v-select
        :items="dc_items"
        v-model="selected_data"
        label="Data"
        hint="Select the data set."
        persistent-hint
      ></v-select>
    </v-row>

    <plugin-subset-select 
      :items="spectral_subset_items"
      :selected.sync="spectral_subset_selected"
      :has_subregions="spectral_subset_selected_has_subregions"
      has_subregions_warning="The selected selected subset has subregions, the entire range will be used, ignoring any gaps."
      label="Spectral region"
      hint="Spectral region to compute the moment map."
    />

    <v-row>
      <v-select
        :items="viewers"
        v-model="selected_viewer"
        label='Plot in Viewer'
        hint='Moment map will replace plot in the specified viewer.  Will also be available in the data dropdown in all image viewers.'
        persistent-hint
      ></v-select>
    </v-row>

    <v-row>
      <v-text-field
        ref="n_moment"
        label="Moment"
        v-model="n_moment"
        hint="The desired moment."
        persistent-hint
        :rules="[() => !!n_moment || 'This field is required']"
      ></v-text-field>
    </v-row>

    <v-row justify="end">
      <j-tooltip tipid='plugin-moment-maps-calculate'>
        <v-btn color="primary" text @click="calculate_moment">Calculate</v-btn>
      </j-tooltip>
    </v-row>

    <div v-if="moment_available">
      <j-plugin-section-header>Results</j-plugin-section-header>
      <v-row>
          <v-text-field
           v-model="filename"
           label="Filename"
           :rules="[() => !!filename || 'This field is required']">
          </v-text-field>
      </v-row>
      <v-row justify="end">
        <j-tooltip tipid='plugin-moment-save-fits'>
          <v-btn color="primary" text @click="save_as_fits">Save as FITS</v-btn>
        </j-tooltip>
      </v-row>
    </div>
  </j-tray-plugin>
</template>
