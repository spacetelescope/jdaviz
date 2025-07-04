<template>
  <j-tray-plugin
    :description="docs_description"
    :link="docs_link || 'https://jdaviz.readthedocs.io/en/'+vdocs+'/'+config+'/plugins.html#aperture-photometry'"
    :uses_active_status="uses_active_status"
    :api_hints_enabled.sync="api_hints_enabled"
    @plugin-ping="plugin_ping($event)"
    :keep_active.sync="keep_active"
    :popout_button="popout_button"
    :scroll_to.sync="scroll_to">

    <j-multiselect-toggle
      :multiselect.sync="multiselect"
      :icon_checktoradial="icon_checktoradial"
      :icon_radialtocheck="icon_radialtocheck"
      tooltip="Toggle batch mode"
    ></j-multiselect-toggle>

    <plugin-dataset-select
      :items="dataset_items"
      :selected.sync="dataset_selected"
      :multiselect="multiselect"
      :show_if_single_entry="false"
      label="Data"
      hint="Select the data for photometry."
      api_hint="plg.dataset = "
      :api_hints_enabled="api_hints_enabled"
    />

    <div v-if='config == "cubeviz" && is_cube'>
      <v-row class="row-no-outside-padding row-min-bottom-padding">
        <v-col>
          <v-text-field
            :value="cube_slice"
            class="mt-0 pt-0"
            label="Slice wavelength"
            hint="Extracts photometry from currently selected cube slice"
            disabled
          ></v-text-field>
        </v-col>
      </v-row>
    </div>

    <div v-if='dataset_selected.length > 0'>
      <plugin-subset-select
        :items="aperture_items"
        :selected.sync="aperture_selected"
        :multiselect="multiselect"
        :show_if_single_entry="true"
        label="Aperture"
        hint="Select aperture region for photometry (cannot be an annulus or composite subset)."
        api_hint="plg.aperture = "
        :api_hints_enabled="api_hints_enabled"
      />

      <v-row v-if="aperture_selected.length && !aperture_selected_validity.is_aperture">
        <span class="v-messages v-messages__message text--secondary" style="color: red !important">
            {{aperture_selected}} is not a valid aperture: {{aperture_selected_validity.aperture_message}}.
        </span>
      </v-row>

      <div v-if="aperture_selected.length > 0">
        <plugin-subset-select
          :items="background_items"
          :selected.sync="background_selected"
          :show_if_single_entry="true"
          label="Background"
          hint="Select subset region for background calculation (cannot be a composite subset)."
          api_hint="plg.background = "
          :api_hints_enabled="api_hints_enabled"
        />

        <v-row v-if="(multiselect && aperture_selected.includes(background_selected)) || aperture_selected === background_selected">
          <span class="v-messages v-messages__message text--secondary" style="color: red !important">
              Background and aperture cannot be set to the same subset
          </span>
        </v-row>

        <v-row v-if="multiselect && background_selected !== 'Manual'">
          <span class="v-messages v-messages__message text--secondary">
            <b>Batch mode:</b> background value will be automatically computed for each selected data entry separately and exposed in the output table.
          </span>
        </v-row>
        <v-row v-else>
          <v-text-field
            v-model.number="background_value"
            type="number"
            hint="Background to subtract"
            :suffix="display_unit"
            :disabled="background_selected!='Manual'"
            persistent-hint
            :label="api_hints_enabled ? 'plg.background_value =' : 'Background value'"
            :class="api_hints_enabled ? 'api-hint' : null"
          >
          </v-text-field>
        </v-row>

        <v-row v-if="multiselect">
          <v-switch
            v-model="pixel_area_multi_auto"
            label="Auto pixel area"
            :hint="pixel_area_multi_auto ? 'Pixel area will be automatically computed for each selected data entry separately and exposed in the output table.' : 'Pixel area will be held fixed at the value below for each iteration.'"
            persistent-hint
          />
        </v-row>
        <v-row v-if="(!multiselect || !pixel_area_multi_auto) && display_solid_angle_unit!='pix2'">

          <v-text-field
            :label="api_hints_enabled ? 'plg.pixel_area =' : 'Pixel area'"
            :class="api_hints_enabled ? 'api-hint' : null"
            v-model.number="pixel_area"
            type="number"
            hint="Pixel area in arcsec squared, only used if data is in units of surface brightness."
            persistent-hint
          >
          </v-text-field>
        </v-row>

        <v-row>
          <v-text-field
            :label="api_hints_enabled ? 'plg.counts_factor =' : 'Counts conversion factor'"
            :class="api_hints_enabled ? 'api-hint' : null"
            v-model.number="counts_factor"
            type="number"
            hint="Factor to convert data unit to counts, in unit of flux/counts"
            persistent-hint
            :rules="[() => counts_factor>=0 || 'Counts conversion factor cannot be negative.']"
          >
          </v-text-field>
        </v-row>

        <v-row v-if="multiselect">
          <v-switch
            v-model="flux_scaling_multi_auto"
            label="Auto flux scaling"
            :hint="flux_scaling_multi_auto ? 'Flux scaling will be automatically computed for each selected data entry separately and exposed in the output table.' : 'Flux scaling will be held fixed at the value below for each iteration.'"
            persistent-hint
          />
        </v-row>
        <v-row v-if="!multiselect || !flux_scaling_multi_auto">
          <v-text-field
            v-model.number="flux_scaling"
            type="number"
            hint="Used in -2.5 * log(flux / flux_scaling)"
            :suffix="flux_scaling_display_unit"
            persistent-hint
            :label="api_hints_enabled ? 'plg.flux_scaling =' : 'Flux scaling'"
            :class="api_hints_enabled ? 'api-hint' : null"
          >
          </v-text-field>
        </v-row>
        <v-row v-if="flux_scaling_warning.length > 0">
          <span class="v-messages v-messages__message text--secondary" style="color: red !important">
            {{flux_scaling_warning}}
          </span>
        </v-row>

        <plugin-select
          v-if="!multiselect"
          :items="plot_types"
          :selected.sync="current_plot_type"
          label="Plot Type"
          hint="Aperture photometry plot type"
          api_hint="plg.current_plot_type = "
          :api_hints_enabled="api_hints_enabled"
        />

        <v-row v-if="!multiselect && current_plot_type==='Radial Profile (Raw)' && aperture_area > 5000">
          <span class="v-messages v-messages__message text--secondary">
              <b>WARNING</b>: Computing and displaying raw profile of an aperture containing ~{{aperture_area}} pixels may be slow or unresponsive.
          </span>
        </v-row>

        <v-row v-if="!multiselect && current_plot_type.indexOf('Radial Profile') != -1">

          <v-switch
            hint="Fit Gaussian1D to radial profile"
            v-model="fit_radial_profile"
            persistent-hint
            :label="api_hints_enabled ? 'plg.fit_radial_profile =' : 'Fit Gaussian'"
            :class="api_hints_enabled ? 'api-hint' : null">
          </v-switch>
        </v-row>

        <v-row justify="end">
          <plugin-action-button
            :results_isolated_to_plugin="true"
            @click="do_aper_phot"
            :spinner="spinner"
            :api_hints_enabled="api_hints_enabled"
            :disabled="aperture_selected === background_selected || !aperture_selected_validity.is_aperture || counts_factor < 0"
          >
            {{ api_hints_enabled ?
              'plg.calculate_photometry()'
              :
              'Calculate'
            }}
          </plugin-action-button>
        </v-row>
      </div>
    </div>

    <v-row v-if="result_failed_msg.length > 0">
      <span class="v-messages v-messages__message text--secondary" style="color: red !important">
          <b>WARNING</b>: {{result_failed_msg}}
      </span>
    </v-row>

    <v-row v-if="!multiselect && plot_available">
      <jupyter-widget :widget="plot_widget"/>
    </v-row>

    <div v-if="!multiselect && plot_available && fit_radial_profile && current_plot_type != 'Curve of Growth'">
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

    <div v-if="!multiselect && result_available">
      <j-plugin-section-header>Photometry Results</j-plugin-section-header>

      <v-row no-gutters>
        <v-col cols=6><U>Result</U></v-col>
        <v-col cols=4><U>Value</U></v-col>
        <v-col cols=2><U>Unit</U></v-col>
      </v-row>
      <v-row
        v-for="item in results"
        :key="item.function"
        no-gutters>
        <v-col style="font-size: 8pt" cols=6>{{ item.function }}</v-col>
        <v-col style="font-size: 9pt" cols=4>{{ item.result }}</v-col>
        <v-col style="font-size: 9pt" cols=2>{{ item.unit }}</v-col>
      </v-row>
    </div>

    <div v-if="result_available">
      <j-plugin-section-header>Results History</j-plugin-section-header>
      <jupyter-widget :widget="table_widget"></jupyter-widget>
    </div>
  </j-tray-plugin>
</template>
