<template>
  <j-tray-plugin
    :description="docs_description || 'Extract a spectrum from a spectral cube.'"
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
              <v-switch
                v-model="show_live_preview"
                label="Show live-extraction"
                hint="Whether to compute/show extraction when making changes to input parameters.  Disable if live-preview becomes laggy."
                persistent-hint
              ></v-switch>
            </v-row>
          </v-expansion-panel-content>
        </v-expansion-panel>
      </v-expansion-panels>
    </v-row>

    <div @mouseover="() => active_step='ap'">
      <j-plugin-section-header :active="active_step==='ap'">Aperture</j-plugin-section-header>

      <plugin-subset-select
        :items="aperture_items"
        :selected.sync="aperture_selected"
        :show_if_single_entry="true"
        label="Spatial aperture"
        hint="Select a spatial region to extract its spectrum."
      />

      <v-row v-if="aperture_selected !== 'Entire Cube' && !aperture_selected_validity.is_aperture">
        <span class="v-messages v-messages__message text--secondary">
            {{aperture_selected}} does not support wavelength dependence (cone support): {{aperture_selected_validity.aperture_message}}.
        </span>
      </v-row>

      <div v-if="aperture_selected_validity.is_aperture">
        <v-row>
          <v-switch
            v-model="wavelength_dependent"
            label="Wavelength dependent"
            hint="Vary aperture linearly with wavelength"
            persistent-hint>
          </v-switch>
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
              label="Wavelength"
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

    <div v-if="dev_bg_support" @mouseover="() => active_step='bg'">
      <j-plugin-section-header :active="active_step==='bg'">Background</j-plugin-section-header>
      <plugin-subset-select
        :items="bg_items"
        :selected.sync="bg_selected"
        :show_if_single_entry="true"
        label="Background"
        hint="Select a spatial region to use for background subtraction."
      />

      <v-row v-if="aperture_selected === bg_selected">
        <span class="v-messages v-messages__message text--secondary" style="color: red !important">
            Background and aperture cannot be set to the same subset
        </span>
      </v-row>

      <v-row v-if="bg_selected !== 'None' && !bg_selected_validity.is_aperture">
        <span class="v-messages v-messages__message text--secondary">
            {{bg_selected}} does not support wavelength dependence (cone support): {{bg_selected_validity.aperture_message}}.
        </span>
      </v-row>

      <div v-if="aperture_selected_validity.is_aperture
                 && bg_selected_validity.is_aperture
                 && wavelength_dependent">
        <v-row>
          <v-switch
            v-model="bg_wavelength_dependent"
            label="Wavelength dependent"
            hint="Vary background linearly with wavelength"
            persistent-hint>
          </v-switch>
        </v-row>
        <div v-if="bg_wavelength_dependent">
          <v-row>
            <v-text-field
              v-model.number="reference_spectral_value"
              type="number"
              :step="0.1"
              class="mt-0 pt-0"
              label="Wavelength"
              hint="Wavelength at which the background matches the selected subset (fixed at same value as for aperture above)."
              persistent-hint
              disabled
            ></v-text-field>
          </v-row>
        </div>
      </div>
    </div>

    <div @mouseover="() => active_step='ext'">
      <j-plugin-section-header :active="active_step==='ext'">Extract</j-plugin-section-header>

      <v-row v-if="aperture_selected !== 'None' && !aperture_selected_validity.is_aperture">
        <span class="v-messages v-messages__message text--secondary">
            Aperture: {{aperture_selected}} does not support subpixel: {{aperture_selected_validity.aperture_message}}.
        </span>
      </v-row>
      <v-row v-if="bg_selected !== 'None' && !bg_selected_validity.is_aperture">
        <span class="v-messages v-messages__message text--secondary">
            Background: {{bg_selected}} does not support subpixel: {{bg_selected_validity.aperture_message}}.
        </span>
      </v-row>


      <div v-if="(aperture_selected === 'Entire Cube' || aperture_selected_validity.is_aperture)
                 && (bg_selected === 'None' || bg_selected_validity.is_aperture)">
        <v-row>
          <v-select
            :menu-props="{ left: true }"
            attach
            :items="aperture_method_items.map(i => i.label)"
            v-model="aperture_method_selected"
            label="Aperture masking method"
            hint="Extract spectrum using an aperture masking method in place of the subset mask."
            persistent-hint
            ></v-select>
          <j-docs-link>
            See the <j-external-link link='https://photutils.readthedocs.io/en/stable/aperture.html#aperture-and-pixel-overlap'
            linktext='photutils docs'></j-external-link>
            for more details on aperture masking methods.
          </j-docs-link>
        </v-row>
      </div>

      <v-row>
        <v-select
          :menu-props="{ left: true }"
          attach
          :items="function_items.map(i => i.label)"
          v-model="function_selected"
          label="Function"
          hint="Function for reducing dimensions of spectral cube."
          persistent-hint
        ></v-select>
      </v-row>
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
        label_hint="Label for the extracted spectrum"
        :add_to_viewer_items="add_to_viewer_items"
        :add_to_viewer_selected.sync="add_to_viewer_selected"
        action_label="Extract"
        action_tooltip="Run spectral extraction with error and mask propagation"
        :action_spinner="spinner"
        :action_disabled="aperture_selected === bg_selected || conflicting_aperture_and_function"
        @click:action="spectral_extraction"
      ></plugin-add-results>

      <j-plugin-section-header v-if="extracted_spec_available && export_enabled">Results</j-plugin-section-header>

      <div style="display: grid; position: relative"> <!-- overlay container -->
        <div style="grid-area: 1/1">
          <div v-if="extracted_spec_available && export_enabled">

            <v-row>
              <v-text-field
              v-model="filename"
              label="Filename"
              hint="Export the latest extracted spectrum."
              :rules="[() => !!filename || 'This field is required']"
              persistent-hint>
              </v-text-field>
            </v-row>

            <v-row>
              <span class="v-messages v-messages__message text--secondary" style="color: red !important">
                DeprecationWarning: Save as FITS functionality has moved to the Export plugin as of v3.9 and will be removed from here in a future release.
              </span>
            </v-row>

            <v-row justify="end">
              <j-tooltip tipid='plugin-extract-save-fits'>
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
    </div>

  </j-tray-plugin>
</template>
