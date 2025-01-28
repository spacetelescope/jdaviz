<template>
  <j-tray-plugin
    :config="config"
    :plugin_key="plugin_key || 'Spectral Extraction'"
    :api_hints_enabled.sync="api_hints_enabled"
    :description="docs_description"
    :link="docs_link || 'https://jdaviz.readthedocs.io/en/'+vdocs+'/'+config+'/plugins.html#spectral-extraction'"
    :uses_active_status="uses_active_status"
    @plugin-ping="plugin_ping($event)"
    :keep_active.sync="keep_active"
    :popout_button="popout_button"
    :scroll_to.sync="scroll_to"
    :disabled_msg="disabled_msg">

    <v-row>
      <v-expansion-panels popout>
        <v-expansion-panel>
          <v-expansion-panel-header v-slot="{ open }">
            <span style="padding: 6px">Settings</span>
          </v-expansion-panel-header>
          <v-expansion-panel-content class="plugin-expansion-panel-content">
            <v-row>
              <plugin-switch
                :value.sync="show_live_preview"
                label="Show live-extraction"
                api_hint="plg.show_live_preview = "
                :api_hints_enabled="api_hints_enabled"
                hint="Whether to compute/show extraction when making changes to input parameters.  Disable if live-preview becomes laggy."
              />
            </v-row>
          </v-expansion-panel-content>
        </v-expansion-panel>
      </v-expansion-panels>
    </v-row>

    <plugin-dataset-select
      :items="dataset_items"
      :selected.sync="dataset_selected"
      :show_if_single_entry="api_hints_enabled"
      label="Data"
      api_hint="plg.dataset ="
      :api_hints_enabled="api_hints_enabled"
      hint="Select the input flux cube."
    />


    <div @mouseover="() => active_step='ap'">
      <j-plugin-section-header :active="active_step==='ap'">Aperture</j-plugin-section-header>

      <plugin-subset-select
        :items="aperture_items"
        :selected.sync="aperture_selected"
        :show_if_single_entry="true"
        label="Spatial aperture"
        api_hint="plg.aperture ="
        :api_hints_enabled="api_hints_enabled"
        :hint="'Select a spatial region to extract its '+resulting_product_name+'.'"
      />

      <div v-if="wavelength_dependent_available">
        <v-row v-if="aperture_selected !== 'Entire Cube' && !aperture_selected_validity.is_aperture">
          <span class="v-messages v-messages__message text--secondary">
              Aperture: '{{aperture_selected}}' does not support wavelength dependence (cone support): {{aperture_selected_validity.aperture_message}}.
          </span>
        </v-row>

        <div v-if="aperture_selected_validity.is_aperture">
          <v-row>
            <plugin-switch
              :value.sync="wavelength_dependent"
              label="Wavelength dependent"
              api_hint="plg.wavelength_dependent = "
              :api_hints_enabled="api_hints_enabled"
              hint="Vary aperture linearly with wavelength"
            />
          </v-row>
          <div v-if="wavelength_dependent">
            <v-row justify="end">
              <j-tooltip tooltipcontent="Adopt the current slice as the reference wavelength">
                <plugin-action-button :results_isolated_to_plugin="true" @click="adopt_slice_as_reference">
                  Adopt Current Slice
                </plugin-action-button>
              </j-tooltip>
            </v-row>
            <v-row>
              <v-text-field
                v-model.number="reference_spectral_value"
                type="number"
                :step="0.1"
                class="mt-0 pt-0"
                :label="api_hints_enabled ? 'plg.reference_spectral_value =' : 'Wavelength'"
                hint="Wavelength at which the aperture matches the selected subset."
                persistent-hint
              ></v-text-field>
            </v-row>
            <v-row justify="end">
              <j-tooltip tooltipcontent="Select the slice nearest the reference wavelength">
                <plugin-action-button :results_isolated_to_plugin="true" @click="goto_reference_spectral_value">
                  Slice to Wavelength
                </plugin-action-button>
              </j-tooltip>
            </v-row>
          </div>
        </div>
      </div>
    </div>

    <div @mouseover="() => active_step='bg'">
      <j-plugin-section-header :active="active_step==='bg'">Background</j-plugin-section-header>
      <plugin-subset-select
        :items="bg_items"
        :selected.sync="bg_selected"
        :show_if_single_entry="true"
        label="Background"
        api_hint="plg.background ="
        :api_hints_enabled="api_hints_enabled"
        hint="Select a spatial region to use for background subtraction."
      />

      <v-row v-if="aperture_selected === bg_selected">
        <span class="v-messages v-messages__message text--secondary" style="color: red !important">
            Background and aperture cannot be set to the same subset
        </span>
      </v-row>

      <v-row v-if="bg_selected !== 'None' && !bg_selected_validity.is_aperture">
        <span class="v-messages v-messages__message text--secondary">
            Background: '{{bg_selected}}' does not support wavelength dependence (cone support): {{bg_selected_validity.aperture_message}}.
        </span>
      </v-row>

      <div v-if="aperture_selected_validity.is_aperture
                 && bg_selected_validity.is_aperture
                 && wavelength_dependent">
        <v-row>
          <plugin-switch
            :value.sync="bg_wavelength_dependent"
            label="Wavelength dependent"
            api_hint="bg_wavelength_dependent ="
            :api_hints_enabled="api_hints_enabled"
            hint="Vary background linearly with wavelength"
          />
        </v-row>
        <div v-if="bg_wavelength_dependent">
          <v-row>
            <v-text-field
              v-model.number="reference_spectral_value"
              type="number"
              :step="0.1"
              class="mt-0 pt-0"
              :label="api_hints_enabled ? 'plg.reference_spectral_value =' : 'Wavelength'"
              hint="Wavelength at which the background matches the selected subset (fixed at same value as for aperture above)."
              persistent-hint
              disabled
            ></v-text-field>
          </v-row>
        </div>
      </div>

      <v-row v-if="bg_selected !== 'None' && bg_export_available">
        <v-expansion-panels accordion>
          <v-expansion-panel>
            <v-expansion-panel-header v-slot="{ open }">
              <span style="padding: 6px; text-transform: capitalize;">Export Background {{resulting_product_name}}</span>
            </v-expansion-panel-header>
            <v-expansion-panel-content class="plugin-expansion-panel-content">
              <v-row v-if="function_selected === 'Sum'">
                <plugin-switch
                  :value.sync="bg_spec_per_spaxel"
                  label="Normalize per-spaxel"
                  api_hint="bg_spec_per_spaxel ="
                  :api_hints_enabled="api_hints_enabled"
                  :hint="'Whether to normalize the background per spaxel (not shown in preview). Otherwise, the '+resulting_product_name+' will be scaled by the ratio between the areas of the extraction aperture to the background aperture.'"
                />
              </v-row>
              <plugin-add-results
                :label.sync="bg_spec_results_label"
                :label_default="bg_spec_results_label_default"
                :label_auto.sync="bg_spec_results_label_auto"
                :label_invalid_msg="bg_spec_results_label_invalid_msg"
                :label_overwrite="bg_spec_results_label_overwrite"
                :label_hint="'Label for the background '+resulting_product_name+'.'"
                :add_to_viewer_items="bg_spec_add_to_viewer_items"
                :add_to_viewer_selected.sync="bg_spec_add_to_viewer_selected"
                action_label="Export"
                :action_tooltip="'Create background '+resulting_product_name"
                add_results_api_hint='plg.bg_spec_results'
                action_api_hint='plg.extract_bg_spectrum(add_data=True)'
                :api_hints_enabled="api_hints_enabled"
                @click:action="create_bg_spec"
              ></plugin-add-results>
            </v-expansion-panel-content>
          </v-expansion-panel>
        </v-expansion-panels>
      </v-row>

    </div>

    <div @mouseover="() => active_step='extract'">
      <j-plugin-section-header :active="active_step==='extract'">Extract</j-plugin-section-header>

      <v-row v-if="aperture_selected !== 'None' && !aperture_selected_validity.is_aperture">
        <span class="v-messages v-messages__message text--secondary">
            Aperture: '{{aperture_selected}}' does not support subpixel: {{aperture_selected_validity.aperture_message}}.
        </span>
      </v-row>
      <v-row v-if="bg_selected !== 'None' && !bg_selected_validity.is_aperture">
        <span class="v-messages v-messages__message text--secondary">
            Background: '{{bg_selected}}' does not support subpixel: {{bg_selected_validity.aperture_message}}.
        </span>
      </v-row>


      <div v-if="((aperture_selected === 'Entire Cube' && bg_selected !== 'None') || aperture_selected_validity.is_aperture)
                 && (bg_selected === 'None' || bg_selected_validity.is_aperture)">
        <plugin-select
          :items="aperture_method_items.map(i => i.label)"
          :selected.sync="aperture_method_selected"
          label="Aperture masking method"
          api_hint="plg.aperture_method ="
          :api_hints_enabled="api_hints_enabled"
          :hint="'Extract '+resulting_product_name+' using an aperture masking method in place of the subset mask.'"
        />
        <v-row>
          <j-docs-link>
              See the <j-external-link link='https://photutils.readthedocs.io/en/stable/aperture.html#aperture-and-pixel-overlap'
              linktext='photutils docs'></j-external-link> for more details on aperture masking methods.
          </j-docs-link>
        </v-row>
      </div>

      <plugin-select
        v-if="function_items.length > 1"
        :items="function_items.map(i => i.label)"
        :selected.sync="function_selected"
        label="Function"
        api_hint="plg.function ="
        :api_hints_enabled="api_hints_enabled"
        :hint="'Function to apply to data in \''+aperture_selected+'\'.'"
      />
      <v-row v-if="conflicting_aperture_and_function">
        <span class="v-messages v-messages__message text--secondary" style="color: red !important">
          {{conflicting_aperture_error_message}}
        </span>
      </v-row>

      <plugin-previews-temp-disabled
        :previews_temp_disabled.sync="previews_temp_disabled"
        :previews_last_time="previews_last_time"
        :show_live_preview.sync="show_live_preview"
      />

      <plugin-add-results
        :label.sync="results_label"
        :label_default="results_label_default"
        :label_auto.sync="results_label_auto"
        :label_invalid_msg="results_label_invalid_msg"
        :label_overwrite="results_label_overwrite"
        :label_hint="'Label for the extracted '+resulting_product_name+'.'"
        :add_to_viewer_items="add_to_viewer_items"
        :add_to_viewer_selected.sync="add_to_viewer_selected"
        :auto_update_result.sync="auto_update_result"
        action_label="Extract"
        action_tooltip="Run spectral extraction with error and mask propagation"
        :action_spinner="spinner"
        add_results_api_hint='plg.add_results'
        action_api_hint='plg.extract(add_data=True)'
        :api_hints_enabled="api_hints_enabled"
        :action_disabled="aperture_selected === bg_selected || conflicting_aperture_and_function"
        @click:action="spectral_extraction"
      >
        <v-alert
          v-if="spectrum_y_units && results_units !== spectrum_y_units"
          type='warning'
          style="margin-left: -12px; margin-right: -12px"
        >
          function='{{ function_selected }}' will result in units of {{ results_units }}, but will be displayed as {{ spectrum_y_units }}.  To change plotted units, see the Unit Conversion plugin
        </v-alert>
      </plugin-add-results>

  </j-tray-plugin>
</template>
