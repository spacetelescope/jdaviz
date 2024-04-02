<template>
  <j-tray-plugin
    :description="docs_description || 'Create a 2D image from a data cube.'"
    :link="docs_link || 'https://jdaviz.readthedocs.io/en/'+vdocs+'/'+config+'/plugins.html#moment-maps'"
    :uses_active_status="uses_active_status"
    @plugin-ping="plugin_ping($event)"
    :keep_active.sync="keep_active"
    :popout_button="popout_button"
    :scroll_to.sync="scroll_to">

    <j-plugin-section-header>Cube</j-plugin-section-header>
    <v-row>
      <j-docs-link>Choose the input cube and spectral subset.</j-docs-link>
    </v-row>

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

    <j-plugin-section-header>Continuum Subtraction</j-plugin-section-header>
    <v-row>
      <j-docs-link v-if="continuum_subset_selected==='None'">
        Choose whether and how to compute the continuum for continuum subtraction.
      </j-docs-link>
      <j-docs-link v-else>
        {{continuum_subset_selected=='Surrounding' && spectral_subset_selected=='Entire Spectrum' ? "Since using the entire spectrum, the end points will be used to fit a linear continuum." : "Choose a region to fit a linear line as the underlying continuum."}}
        {{continuum_subset_selected=='Surrounding' && spectral_subset_selected!='Entire Spectrum' ? "Choose a width in number of data points to consider on each side of the line region defined above." : null}}
        When this plugin is opened, a visual indicator will show on the spectrum plot showing the continuum fitted as a thick line, and interpolated into the line region as a thin line.
        When computing the moment map, these same input options will be used to compute and subtract a linear continuum for each spaxel, independently.
      </j-docs-link>
    </v-row>

    <plugin-subset-select
      :items="continuum_subset_items"
      :selected.sync="continuum_subset_selected"
      :show_if_single_entry="true"
      :rules="[() => continuum_subset_selected!==spectral_subset_selected || 'Must not match line selection.']"
      label="Continuum"
      hint="Select spectral region that defines the continuum."
    />

    <v-row v-if="continuum_subset_selected=='Surrounding' && spectral_subset_selected!='Entire Spectrum'">
      <!-- DEV NOTE: if changing the validation rules below, also update the logic to clear the results
           in line_analysis.py  -->
      <v-text-field
        label="Width"
        type="number"
        v-model.number="continuum_width"
        step="0.1"
        :rules="[() => continuum_width!=='' || 'This field is required.',
                 () => continuum_width<=10 || 'Width must be <= 10.',
                 () => continuum_width>=1 || 'Width must be >= 1.']"
        hint="Width, relative to the overall line spectral region, to fit the linear continuum (excluding the region containing the line).  If 1, will use endpoints within line region only."
        persistent-hint
      >
      </v-text-field>
    </v-row>

    <j-plugin-section-header>Moment</j-plugin-section-header>
    <v-row>
      <j-docs-link>Options for generating the moment map.</j-docs-link>
    </v-row>

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

    <div v-if="dataset_spectral_unit !== ''">
      <v-row>
        <v-radio-group
          label="Output Units"
          hint="Choose the output units for calculated moment."
          v-model="output_unit_selected"
          column
          class="no-hint">
          <v-radio
            v-for="item in output_radio_items"
            :key="item.label"
            :label="item.label + ' (' + item.unit_str + ')'"
            :value="item.label"
          ></v-radio>
        </v-radio-group>
      </v-row>
      <v-row v-if="output_unit_selected !== 'Spectral Unit' && output_unit_selected !== 'Flux'">
        <v-text-field
        ref="reference_wavelength"
        type="number"
        label="Reference Wavelength"
        v-model.number="reference_wavelength"
        :suffix="dataset_spectral_unit.replace('Angstrom', 'A')"
        hint="Observed wavelength of the line of interest"
        persistent-hint
        :rules="[() => reference_wavelength !== '' || 'This field is required',
                 () => reference_wavelength > 0 || 'Wavelength must be positive']"
        ></v-text-field>
      </v-row>
    </div>

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
      :action_disabled="n_moment > 0 && output_unit_selected !== 'Spectral Unit' && reference_wavelength === 0"
      @click:action="calculate_moment"
    ></plugin-add-results>

    <v-row v-if="n_moment > 0 && output_unit_selected === 'Flux'">
      <span class="v-messages v-messages__message text--secondary" style="color: red !important">
          Cannot calculate moment: Output unit set to invalid value from API.
      </span>
    </v-row>

    <v-row v-else-if="n_moment > 0 && output_unit_selected !== 'Spectral Unit' && reference_wavelength === 0">
      <span class="v-messages v-messages__message text--secondary" style="color: red !important">
          Cannot calculate moment: Must set reference wavelength for output in velocity units.
      </span>
    </v-row>

    <j-plugin-section-header v-if="moment_available && export_enabled">Results</j-plugin-section-header>

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

          <v-row>
            <span class="v-messages v-messages__message text--secondary" style="color: red !important">
                DeprecationWarning: Save as FITS functionality has moved to the Export plugin as of v3.9 and will be removed from Moment Maps plugin in a future release.
            </span>
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
