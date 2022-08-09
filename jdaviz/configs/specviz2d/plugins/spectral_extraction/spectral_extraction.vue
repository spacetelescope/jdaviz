<template>
  <j-tray-plugin
    description="2D to 1D spectral extraction."
    :link="'https://jdaviz.readthedocs.io/en/'+vdocs+'/'+config+'/plugins.html#spectral-extraction'"
    :popout_button="popout_button">

    <v-row>
      <v-expansion-panels popout>
        <v-expansion-panel>
          <v-expansion-panel-header v-slot="{ open }">
            <span style="padding: 6px">Settings</span>
          </v-expansion-panel-header>
          <v-expansion-panel-content>
            <v-row>
              <v-switch
                v-model="setting_interactive_extract"
                label="Show live-extraction"
                hint="Whether to compute/show extraction when making changes to input parameters.  Disable if live-preview becomes laggy."
                persistent-hint
              ></v-switch>
            </v-row>
          </v-expansion-panel-content>
        </v-expansion-panel>
      </v-expansion-panels>
    </v-row>


    <div @mouseover="() => active_step='trace'">
      <j-plugin-section-header>Trace</j-plugin-section-header>
      <v-row>
        <j-docs-link>Create a trace for the spectrum.</j-docs-link>
      </v-row>

      <div>
        <plugin-dataset-select
          :items="trace_dataset_items"
          :selected.sync="trace_dataset_selected"
          :show_if_single_entry="false"
          label="2D Spectrum"
          hint="Select the data used to create the trace."
        />

        <v-row>
          <v-select
            :items="trace_type_items"
            v-model="trace_type_selected"
            label="Trace Type"
            hint="Method to use for creating trace"
            persistent-hint
          ></v-select>
        </v-row>

        <v-row>
          <v-text-field
            label="Pixel"
            type="number"
            v-model.number="trace_pixel"
            :rules="[() => trace_pixel!=='' || 'This field is required']"
            :hint="trace_type_selected === 'Flat' ? 'Pixel number/column for the trace.' : 'Pixel number/column guess'"
            persistent-hint
          >
          </v-text-field>
        </v-row>

        <v-row v-if="trace_type_selected==='Auto'">
          <v-text-field
            label="Bins"
            type="number"
            v-model.number="trace_bins"
            :rules="[() => trace_bins!=='' || 'This field is required']"
            hint="Number of bins in the dispersion direction."
            persistent-hint
          >
          </v-text-field>
        </v-row>

        <v-row v-if="trace_type_selected==='Auto'">
          <v-text-field
            label="Window Width"
            type="number"
            v-model.number="trace_window"
            :rules="[() => trace_window!=='' || 'This field is required']"
            hint="Width of window to consider for peak finding."
            persistent-hint
          >
          </v-text-field>
        </v-row>

        <v-row v-if="trace_type_selected==='Auto'">
          <v-select
            :items="trace_peak_method_items"
            v-model="trace_peak_method_selected"
            label="Peak Method"
            hint="Method to use for identifying the peak cross-dispersion pixel in each bin"
            persistent-hint
          ></v-select>
        </v-row>
      </div>
    </div>

    <div @mouseover="() => active_step='bg'">
      <j-plugin-section-header>Background</j-plugin-section-header>
      <v-row>
        <j-docs-link>Create a background and/or background-subtracted image.</j-docs-link>
      </v-row>

      <v-row v-if="ext_dataset_selected !== 'From Plugin'">
        <span class="v-messages v-messages__message text--secondary">
          <b style="color: red !important">NOTE:</b> extracted spectrum is using "{{ext_dataset_selected}}" as input data, so will not update in real-time.  Switch to "From Plugin" to use the background subtraction defined here.
        </span>
      </v-row>

      <plugin-dataset-select
        :items="bg_dataset_items"
        :selected.sync="bg_dataset_selected"
        :show_if_single_entry="false"
        label="2D Spectrum"
        hint="Select the data used to determine the background."
      />

      <v-row>
        <v-select
          :items="bg_type_items"
          v-model="bg_type_selected"
          label="Background Type"
          hint="Method to use for creating background"
          persistent-hint
        ></v-select>
      </v-row>

      <v-row v-if="bg_type_selected === 'Manual'">
        <v-text-field
          label="Pixel"
          type="number"
          v-model.number="bg_trace_pixel"
          :rules="[() => bg_trace_pixel!=='' || 'This field is required']"
          hint="Pixel number/column to use for the center of the manual background window."
          persistent-hint
        >
        </v-text-field>
      </v-row>

      <v-row v-if="['OneSided', 'TwoSided'].indexOf(bg_type_selected) !== -1">
        <v-text-field
          label="Separation"
          type="number"
          v-model.number="bg_separation"
          :rules="[() => bg_separation!=='' || 'This field is required']"
          hint="Separation between trace and center of the background window(s), in pixels."
          persistent-hint
        >
        </v-text-field>
      </v-row>

      <v-row>
        <v-text-field
          label="Width"
          type="number"
          v-model.number="bg_width"
          :rules="[() => bg_width!=='' || 'This field is required']"
          hint="Width of background window, in pixels."
          persistent-hint
        >
        </v-text-field>
      </v-row>

      <v-row>
        <v-expansion-panels popout>
          <v-expansion-panel>
            <v-expansion-panel-header v-slot="{ open }">
              <span style="padding: 6px">Export Background</span>
            </v-expansion-panel-header>
            <v-expansion-panel-content>
              <plugin-add-results
                :label.sync="bg_results_label"
                :label_default="bg_results_label_default"
                :label_auto.sync="bg_results_label_auto"
                :label_invalid_msg="bg_results_label_invalid_msg"
                :label_overwrite="bg_results_label_overwrite"
                label_hint="Label for the background image"
                :add_to_viewer_items="bg_add_to_viewer_items"
                :add_to_viewer_selected.sync="bg_add_to_viewer_selected"
                action_label="Export"
                action_tooltip="Create Background Image"
                @click:action="create_bg_img"
              ></plugin-add-results>
            </v-expansion-panel-content>
          </v-expansion-panel>
        </v-expansion-panels>
      </v-row>
      <v-row>
        <v-expansion-panels popout>
          <v-expansion-panel>
            <v-expansion-panel-header v-slot="{ open }">
              <span style="padding: 6px">Export Subtracted</span>
            </v-expansion-panel-header>
            <v-expansion-panel-content>
              <plugin-add-results
                :label.sync="bg_sub_results_label"
                :label_default="bg_sub_results_label_default"
                :label_auto.sync="bg_sub_results_label_auto"
                :label_invalid_msg="bg_sub_results_label_invalid_msg"
                :label_overwrite="bg_sub_results_label_overwrite"
                label_hint="Label for the background-subtracted image"
                :add_to_viewer_items="bg_sub_add_to_viewer_items"
                :add_to_viewer_selected.sync="bg_sub_add_to_viewer_selected"
                action_label="Export"
                action_tooltip="Create Background Subtracted Image"
                @click:action="create_bg_sub"
              ></plugin-add-results>
            </v-expansion-panel-content>
          </v-expansion-panel>
        </v-expansion-panels>
      </v-row>
    </div>

    <div @mouseover="() => active_step='ext'">
      <j-plugin-section-header>Extraction</j-plugin-section-header>
      <v-row>
        <j-docs-link>Extract a 1D spectrum from a 2D spectrum.</j-docs-link>
      </v-row>

      <plugin-dataset-select
        :items="ext_dataset_items"
        :selected.sync="ext_dataset_selected"
        :show_if_single_entry="false"
        label="2D Spectrum"
        hint="Select the data used to extract the spectrum.  'From Plugin' uses background-subtraced image defined in Background section above."
      />

      <v-row>
        <v-text-field
          label="Width"
          type="number"
          v-model.number="ext_width"
          :rules="[() => ext_width!=='' || 'This field is required']"
          hint="Width of extraction window, in pixels."
          persistent-hint
        >
        </v-text-field>
      </v-row>

      <plugin-add-results
        :label.sync="ext_results_label"
        :label_default="ext_results_label_default"
        :label_auto.sync="ext_results_label_auto"
        :label_invalid_msg="ext_results_label_invalid_msg"
        :label_overwrite="ext_results_label_overwrite"
        label_hint="Label for the extracted 1D spectrum"
        :add_to_viewer_items="ext_add_to_viewer_items"
        :add_to_viewer_selected.sync="ext_add_to_viewer_selected"
        action_label="Extract"
        action_tooltip="Extract 1D Spectrum"
        :action_disabled="ext_specreduce_err.length"
        @click:action="extract_spectrum"
      ></plugin-add-results>
    </div>

    <v-row v-if="ext_specreduce_err">
      <span class="v-messages v-messages__message text--secondary">
        <b style="color: red !important">ERROR from specreduce:</b> {{ext_specreduce_err}}
      </span>
    </v-row>

    </div>
  </j-tray-plugin>
</template>
