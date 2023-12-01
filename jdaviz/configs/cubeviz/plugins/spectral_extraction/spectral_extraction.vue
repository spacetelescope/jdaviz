<template>
  <j-tray-plugin
    description='Extract a spectrum from a spectral cube.'
    :link="docs_link || 'https://jdaviz.readthedocs.io/en/'+vdocs+'/'+config+'/plugins.html#spectral-extraction'"
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
      :items="spatial_subset_items"
      :selected.sync="spatial_subset_selected"
      :show_if_single_entry="true"
      label="Spatial region"
      hint="Select a spatial region to extract its spectrum."
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
