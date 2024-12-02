<template>
  <j-tray-plugin
    :description="docs_description"
    :link="docs_link || 'https://jdaviz.readthedocs.io/en/'+vdocs+'/'+config+'/plugins.html#ramp-extraction'"
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
                label="Show live ramp extraction"
                hint="Whether to compute/show extraction when making changes to input parameters.  Disable if live-preview becomes laggy."
                persistent-hint
              ></v-switch>
            </v-row>
            <v-row>
              <v-switch
                v-model="show_subset_preview"
                label="Show subset ramp profiles"
                hint="Show each pixel's ramp profile within a subset."
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
        :hint="'Select a spatial region to extract its '+resulting_product_name+'.'"
      />
      <v-alert v-if="subset_preview_warning" type='warning' style="margin-left: -12px; margin-right: -12px">
        For subsets with >{{subset_preview_limit}} pixels, subset ramp previews will be shown
        for {{subset_preview_limit}} randomly drawn pixels from within the subset.
      </v-alert>
    </div>

    <div @mouseover="() => active_step='extract'">
      <j-plugin-section-header :active="active_step==='extract'">Extract</j-plugin-section-header>

      <v-row>
        <span class="v-messages v-messages__message text--secondary">
          Note: this plugin does not detecting defects in ramps, fit the ramps, or apply corrections. For details on
          how rate images are derived from ramps, see the documentation for the
          <j-external-link link='https://roman-pipeline.readthedocs.io/en/stable/roman/ramp_fitting/index.html' linktext='Roman pipeline'>
          </j-external-link> or the
          <j-external-link link='https://jwst-pipeline.readthedocs.io/en/stable/jwst/ramp_fitting/index.html#ramp-fitting-step' linktext='JWST pipeline'>
          </j-external-link>.
        </span>
      </v-row>

      <v-row v-if="aperture_selected !== 'None' && !aperture_selected_validity.is_aperture">
        <span class="v-messages v-messages__message text--secondary">
            Aperture: '{{aperture_selected}}' does not support subpixel: {{aperture_selected_validity.aperture_message}}.
        </span>
      </v-row>

      <plugin-select
        :items="function_items.map(i => i.label)"
        :selected.sync="function_selected"
        label="Function"
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
        action_tooltip="Run ramp extraction with error and mask propagation"
        :action_spinner="spinner"
        :action_disabled="conflicting_aperture_and_function"
        @click:action="ramp_extraction"
      ></plugin-add-results>

      <j-plugin-section-header v-if="extraction_available && export_enabled">Results</j-plugin-section-header>

      <div style="display: grid; position: relative"> <!-- overlay container -->
        <div style="grid-area: 1/1">
          <div v-if="extraction_available && export_enabled">

            <v-row>
              <v-text-field
              v-model="filename"
              label="Filename"
              hint="Export the latest extracted ramp profile."
              :rules="[() => !!filename || 'This field is required']"
              persistent-hint>
              </v-text-field>
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
            </v-row>
          </v-card-actions>
        </v-card>

        </v-overlay>
      </div>
    </div>

  </j-tray-plugin>
</template>
<script setup lang="ts">
</script>