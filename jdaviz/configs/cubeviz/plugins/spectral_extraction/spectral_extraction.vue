<template>
  <j-tray-plugin
    description='Extract a spectrum from a spectral cube.'
    :link="docs_link || 'https://jdaviz.readthedocs.io/en/'+vdocs+'/'+config+'/plugins.html#spectral-extraction'"
    :uses_active_status="uses_active_status"
    @plugin-ping="plugin_ping($event)"
    :keep_active.sync="keep_active"
    :popout_button="popout_button"
    :disabled_msg="disabled_msg">

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

    <plugin-subset-select 
      :items="aperture_items"
      :selected.sync="aperture_selected"
      :show_if_single_entry="true"
      label="Spatial aperture"
      hint="Select a spatial region to extract its spectrum."
    />

    <div v-if="aperture_selected !== 'Entire Cube' && dev_cone_support">
      <v-alert type='warning'>cone support is under active development and hidden from users</v-alert>
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
            v-model.number="reference_wavelength"
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
            <plugin-action-button :results_isolated_to_plugin="true" @click="goto_reference_wavelength">
              Slice to Reference Wavelength
            </plugin-action-button>
          </j-tooltip>
        </v-row>
      </div>

    </div>

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
  </j-tray-plugin>
</template>
