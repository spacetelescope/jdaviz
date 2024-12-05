<template>
  <j-tray-plugin
    :config="config"
    plugin_key="Moment Maps"
    :api_hints_enabled.sync="api_hints_enabled"
    :description="docs_description"
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
      api_hint="plg.dataset ="
      :api_hints_enabled="api_hints_enabled"
      hint="Select the data set."
    />

    <plugin-subset-select
      :items="spectral_subset_items"
      :selected.sync="spectral_subset_selected"
      :has_subregions="spectral_subset_selected_has_subregions"
      :show_if_single_entry="true"
      has_subregions_warning="The selected selected subset has subregions, the entire range will be used, ignoring any gaps."
      label="Spectral region"
      api_hint="plg.spectral_subset ="
      :api_hints_enabled="api_hints_enabled"
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
      api_hint="plg.continuum_subset ="
      :api_hints_enabled="api_hints_enabled"
      hint="Select spectral region that defines the continuum."
    />

    <plugin-dataset-select
      v-if="continuum_subset_selected !== 'None'"
      :items="continuum_dataset_items"
      :selected.sync="continuum_dataset_selected"
      :show_if_single_entry="false"
      label="Continuum Spectrum"
      api_hint="plg.continuum_dataset ="
      :api_hints_enabled="api_hints_enabled"
      hint="Select the spectrum used to visualize the continuum inputs.  The continuum will be recomputed on the input cube when computing the moment map."
    />

    <v-row v-if="continuum_subset_selected=='Surrounding' && spectral_subset_selected!='Entire Spectrum'">
      <!-- DEV NOTE: if changing the validation rules below, also update the logic to clear the results
           in line_analysis.py  -->
      <v-text-field
        :label="api_hints_enabled ? 'plg.continuum_width =' : 'Width'"
        :class="api_hints_enabled ? 'api-hint' : null"
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
        :label="api_hints_enabled ? 'plg.n_moment =' : 'Moment'"
        :class="api_hints_enabled ? 'api-hint' : null"
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
          :label="api_hints_enabled ? 'plg.output_unit =' : 'Output Units'"
          :class="api_hints_enabled ? 'api-hint' : null"
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
      <v-row v-if="output_unit_selected !== 'Spectral Unit' && output_unit_selected !== 'Surface Brightness'">
        <v-text-field
        ref="reference_wavelength"
        type="number"
        :label="api_hints_enabled ? 'plg.reference_wavelength =' : 'Reference Wavelength'"
        :class="api_hints_enabled ? 'api-hint' : null"
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
      add_results_api_hint = 'plg.add_results'
      action_api_hint='plg.calculate_moment(add_data=True)'
      :api_hints_enabled="api_hints_enabled"
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
  </j-tray-plugin>
</template>
