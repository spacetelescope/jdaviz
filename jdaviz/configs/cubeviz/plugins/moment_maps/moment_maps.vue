<template>
  <j-tray-plugin
    description='Create a 2D image from a data cube.'
    :link="docs_link || 'https://jdaviz.readthedocs.io/en/'+vdocs+'/'+config+'/plugins.html#moment-maps'"
    :popout_button="popout_button">

    <plugin-dataset-select
      :items="dataset_items"
      :selected.sync="dataset_selected"
      :show_if_single_entry="false"
      label="Data"
      hint="Select the data set."
    />

    <plugin-subset-select
      :items="spectral_subset_items"
      :selected.sync="spectral_subset_selected"
      :has_subregions="spectral_subset_selected_has_subregions"
      :show_if_single_entry="true"
      has_subregions_warning="The selected selected subset has subregions, the entire range will be used, ignoring any gaps."
      label="Spectral region"
      hint="Spectral region to compute the moment map."
    />

    <v-row>
      <v-text-field
        ref="n_moment"
        type="number"
        label="Moment"
        v-model.number="n_moment"
        hint="The desired moment."
        persistent-hint
        :rules="[() => n_moment !== '' || 'This field is required',
                 () => n_moment >=0 || 'Moment must be positive']"
      ></v-text-field>
    </v-row>

    <v-div v-if="n_moment > 0">
      <v-row>
        <v-radio-group
          label="Output units"
          hint="Choose whether calculated moment is in units of wavelength or velocity."
          v-model="output_unit_selected"
          row>
          <v-radio
            v-for="item in output_unit_items"
            :key="item.label"
            :label="item.label"
            :value="item.label"
          ></v-radio>
        </v-radio-group>
    </v-row>
    <v-row v-if="output_unit_selected === 'Velocity'" align="center">
      <v-col cols="9">
        <v-text-field
        ref="reference_wavelength"
        type="number"
        label="Reference Wavelength"
        v-model.number="reference_wavelength"
        hint="Rest wavelength of the line of interest"
        persistent-hint
        :rules="[() => reference_wavelength !== '' || 'This field is required',
                 () => reference_wavelength >=0 || 'Wavelength must be positive']"
        ></v-text-field>
      </v-col>
      <v-col cols="3" justify="left">{{dataset_spectral_unit}}</v-col>
    </v-row>
    </v-div>

    <plugin-add-results
      :label.sync="results_label"
      :label_default="results_label_default"
      :label_auto.sync="results_label_auto"
      :label_invalid_msg="results_label_invalid_msg"
      :label_overwrite="results_label_overwrite"
      label_hint="Label for the collapsed cube"
      :add_to_viewer_items="add_to_viewer_items"
      :add_to_viewer_selected.sync="add_to_viewer_selected"
      action_label="Calculate"
      action_tooltip="Calculate moment map"
      :action_spinner="spinner"
      @click:action="calculate_moment"
    ></plugin-add-results>

    <j-plugin-section-header v-if="export_enabled">Results</j-plugin-section-header>

    <div style="display: grid; position: relative"> <!-- overlay container -->
      <div style="grid-area: 1/1">
        <div v-if="moment_available && export_enabled">
          <v-row>
              <v-text-field
              v-model="filename"
              label="Filename"
              hint="Export the latest calculated moment map"
              :rules="[() => !!filename || 'This field is required']"
              persistent-hint>
              </v-text-field>
          </v-row>

          <v-row justify="end">
            <j-tooltip tipid='plugin-moment-save-fits'>
              <v-btn color="primary" text @click="save_as_fits">Save as FITS</v-btn>

            </j-tooltip>
          </v-row>

        </div>
      </div>

      <v-overlay
        absolute
        opacity=1.0
        :value="overwrite_warn && export_enabled"
        :zIndex=3
        style="grid-area: 1/1;
               margin-left: -24px;
               margin-right: -24px">

      <v-card color="transparent" elevation=0 >
        <v-card-text width="100%">
          <div class="white--text">
            A file with this name is already on disk. Overwrite?
          </div>
        </v-card-text>

        <v-card-actions>
          <v-row justify="end">
            <v-btn tile small color="primary" class="mr-2" @click="overwrite_warn=false">Cancel</v-btn>
            <v-btn tile small color="accent" class="mr-4" @click="overwrite_fits" >Overwrite</v-btn>
          </v-row>
        </v-card-actions>
      </v-card>

      </v-overlay>


    </div>
  </j-tray-plugin>
</template>
