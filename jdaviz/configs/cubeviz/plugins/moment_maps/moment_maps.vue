<template>
  <j-tray-plugin
    description='Create a 2D image from a data cube.'
    :link="'https://jdaviz.readthedocs.io/en/'+vdocs+'/'+config+'/plugins.html#moment-maps'"
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
      @click:action="calculate_moment"
    ></plugin-add-results>
    
    <j-plugin-section-header>Results</j-plugin-section-header>

    <div style="display: grid; position: relative"> <!-- overlay container -->
      <div style="grid-area: 1/1">
        <div v-if="moment_available">
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
        :value="overwrite_warn"
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
