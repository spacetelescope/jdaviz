<template>
  <j-tray-plugin
    description='Perform aperture photometry for a single region.'
    :link="'https://jdaviz.readthedocs.io/en/'+vdocs+'/'+config+'/plugins.html#simple-aperture-photometry'"
    :popout_button="popout_button">

    <plugin-dataset-select
      :items="dataset_items"
      :selected.sync="dataset_selected"
      :show_if_single_entry="false"
      label="Data"
      hint="Select the data for photometry."
    />

    <div v-if='dataset_selected'>
      <plugin-subset-select
        :items="subset_items"
        :selected.sync="subset_selected"
        :show_if_single_entry="true"
        label="Aperture"
        hint="Select aperture region for photometry (cannot be an annulus or composite subset)."
      />

      <div v-if="subset_selected">
        <plugin-subset-select
          :items="bg_subset_items"
          :selected.sync="bg_subset_selected"
          :show_if_single_entry="true"
          label="Background"
          hint="Select subset region for background calculation (cannot be a composite subset)."
        />

        <v-row v-if="subset_selected === bg_subset_selected">
          <span class="v-messages v-messages__message text--secondary" style="color: red !important">
              Background and aperture cannot be set to the same subset
          </span>
        </v-row>

        <v-row>
          <v-text-field
            label="Background value"
            v-model.number="background_value"
            type="number"
            hint="Background to subtract, same unit as data"
            :disabled="bg_subset_selected!='Manual'"
            persistent-hint
          >
          </v-text-field>
        </v-row>

        <v-row>
          <v-text-field
            label="Pixel area"
            v-model.number="pixel_area"
            type="number"
            hint="Pixel area in arcsec squared, only used if sr in data unit"
            persistent-hint
          >
          </v-text-field>
        </v-row>

        <v-row>
          <v-text-field
            label="Counts conversion factor"
            v-model.number="counts_factor"
            type="number"
            hint="Factor to convert data unit to counts, in unit of flux/counts"
            persistent-hint
          >
          </v-text-field>
        </v-row>

        <v-row>
          <v-text-field
            label="Flux scaling"
            v-model.number="flux_scaling"
            type="number"
            hint="Same unit as data, used in -2.5 * log(flux / flux_scaling)"
            persistent-hint
          >
          </v-text-field>
        </v-row>

        <v-row>
          <v-select
            :menu-props="{ left: true }"
            attach
            :items="plot_types"
            v-model="current_plot_type"
            label="Plot Type"
            hint="Aperture photometry plot type"
            persistent-hint
          ></v-select>
        </v-row>

        <v-row v-if="current_plot_type==='Radial Profile (Raw)' && subset_area > 5000">
          <span class="v-messages v-messages__message text--secondary">
              <b>WARNING</b>: Computing and displaying raw profile of an aperture containing ~{{subset_area}} pixels may be slow or unresponsive.
          </span>
        </v-row>

        <v-row v-if="current_plot_type.indexOf('Radial Profile') != -1">

          <v-switch
            label="Fit Gaussian"
            hint="Fit Gaussian1D to radial profile"
            v-model="fit_radial_profile"
            persistent-hint>
          </v-switch>
        </v-row>

        <v-row justify="end">
          <v-btn color="primary" text @click="do_aper_phot" :disabled="subset_selected === bg_subset_selected">Calculate</v-btn>
        </v-row>
      </div>
    </div>

    <v-row v-if="result_failed_msg.length > 0">
      <span class="v-messages v-messages__message text--secondary" style="color: red !important">
          <b>WARNING</b>: {{result_failed_msg}}
      </span>
    </v-row>

    <v-row v-if="plot_available">
      <jupyter-widget :widget="plot_widget"/> 
    </v-row>

    <div v-if="plot_available && fit_radial_profile && current_plot_type != 'Curve of Growth'">
      <j-plugin-section-header>Gaussian Fit Results</j-plugin-section-header>
      <v-row no-gutters>
        <v-col cols=6><U>Result</U></v-col>
        <v-col cols=6><U>Value</U></v-col>
      </v-row>
      <v-row
        v-for="item in fit_results"
        :key="item.function"
        no-gutters>
        <v-col cols=6>
          {{  item.function  }}
        </v-col>
        <v-col cols=6>{{ item.result }}</v-col>
      </v-row>
    </div>

    <div v-if="result_available">
      <j-plugin-section-header>Photometry Results</j-plugin-section-header>

      <v-row no-gutters>
        <v-col cols=6><U>Result</U></v-col>
        <v-col cols=6><U>Value</U></v-col>
      </v-row>
      <v-row
        v-for="item in results"
        :key="item.function"
        no-gutters>
        <v-col cols=6>
          {{  item.function  }}
        </v-col>
        <v-col cols=6>{{ item.result }}</v-col>
      </v-row>

      <j-plugin-section-header>Results History</j-plugin-section-header>
      <jupyter-widget :widget="table_widget"></jupyter-widget> 
    </div>
  </j-tray-plugin>
</template>
