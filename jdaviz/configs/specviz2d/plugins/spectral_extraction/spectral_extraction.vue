<template>
  <j-tray-plugin
    :config="config"
    plugin_key="Spectral Extraction"
    :api_hints_enabled.sync="api_hints_enabled"
    :description="docs_description"
    :link="docs_link || 'https://jdaviz.readthedocs.io/en/'+vdocs+'/'+config+'/plugins.html#spectral-extraction'"
    :uses_active_status="uses_active_status"
    @plugin-ping="plugin_ping($event)"
    :keep_active.sync="keep_active"
    :popout_button="popout_button"
    :scroll_to.sync="scroll_to">

    <v-row>
      <v-expansion-panels popout>
        <v-expansion-panel>
          <v-expansion-panel-header v-slot="{ open }">
            <span style="padding: 6px">Settings</span>
          </v-expansion-panel-header>
          <v-expansion-panel-content class="plugin-expansion-panel-content">
            <v-row>
              <plugin-switch
                :value.sync="interactive_extract"
                label="Show live-extraction"
                api_hint="plg.interactive_extract = "
                :api_hints_enabled="api_hints_enabled"
                hint="Whether to compute/show extraction when making changes to input parameters.  Disable if live-preview becomes laggy."
              />
            </v-row>
          </v-expansion-panel-content>
        </v-expansion-panel>
      </v-expansion-panels>
    </v-row>


    <div @mouseover="() => active_step='trace'">
      <j-plugin-section-header :active="active_step==='trace'">Trace</j-plugin-section-header>
      <v-row>
        <j-docs-link>
          Create a trace for the spectrum.  See the <j-external-link link='https://specreduce.readthedocs.io/en/latest/#module-specreduce.tracing' linktext='specreduce docs'></j-external-link> for more details on the available trace types.
        </j-docs-link>
      </v-row>

      <plugin-dataset-select
        :items="trace_trace_items"
        :selected.sync="trace_trace_selected"
        :show_if_single_entry="false"
        label="Trace"
        api_hint="plg.trace_trace ="
        :api_hints_enabled="api_hints_enabled"
        hint="Existing trace to offset or create a new trace"
      />

      <div v-if="trace_trace_selected !== 'New Trace'">
        <v-row>
          <v-text-field
            :label="api_hints_enabled ? 'plg.trace_offset =' : 'Offset'"
            :class="api_hints_enabled ? 'api-hint' : null"
            type="number"
            v-model.number="trace_offset"
            :rules="[() => trace_offset!=='' || 'This field is required']"
            hint="Offset to apply to existing trace, in pixels."
            persistent-hint
          >
          </v-text-field>
        </v-row>
      </div>
      <div v-else>
        <plugin-dataset-select
          :items="trace_dataset_items"
          :selected.sync="trace_dataset_selected"
          :show_if_single_entry="false"
          label="2D Spectrum"
          api_hint="plg.trace_dataset ="
          :api_hints_enabled="api_hints_enabled"
          hint="Select the data used to create the trace."
        />

        <plugin-select
          :items="trace_type_items.map(i => i.label)"
          :selected.sync="trace_type_selected"
          label="Trace Type"
          api_hint="plg.trace_type ="
          :api_hints_enabled="api_hints_enabled"
          hint="Method to use for creating trace"
        />

        <v-row v-if="trace_type_selected!=='Flat'">
          <v-text-field
            :label="api_hints_enabled ? 'plg.trace_order =' : 'Order'"
            :class="api_hints_enabled ? 'api-hint' : null"
            type="number"
            v-model.number="trace_order"
            :rules="[() => trace_order!=='' || 'This field is required',
                     () => trace_order>=0 || 'Order must be positive',
                     () => (trace_type_selected!=='Spline' || (trace_order > 0 && trace_order <= 5)) || 'Spline order must be between 1 and 5']"
            hint="Order of the trace model."
            persistent-hint
          >
          </v-text-field>
        </v-row>

        <v-row>
          <v-text-field
            :label="api_hints_enabled ? 'plg.trace_pixel = ' : 'Pixel'"
            :class="api_hints_enabled ? 'api-hint' : null"
            type="number"
            v-model.number="trace_pixel"
            :rules="[() => trace_pixel!=='' || 'This field is required']"
            :hint="trace_type_selected === 'Flat' ? 'Pixel row for flat trace.' : 'Pixel row initial guess for fitting the trace.'"
            persistent-hint
          >
          </v-text-field>
        </v-row>

        <v-row v-if="trace_type_selected!=='Flat'">
          <plugin-switch
            :value.sync="trace_do_binning"
            label="Bin input spectrum"
            api_hint="plg.trace_do_binning ="
            :api_hints_enabled="api_hints_enabled"
          />
          <v-text-field
            v-if="trace_do_binning"
            :label="api_hints_enabled ? 'plg.trace_bins =' : 'Bins'"
            :class="api_hints_enabled ? 'api-hint' : null"
            type="number"
            v-model.number="trace_bins"
            :rules="[() => trace_bins!=='' || 'This field is required',
                     () => trace_bins>=Math.max(4, trace_order+1) || 'Bins must be >= '+Math.max(4, trace_order+1)]"
            hint="Number of bins in the dispersion direction."
            persistent-hint
          >
          </v-text-field>
        </v-row>

        <v-row v-if="trace_type_selected!=='Flat' && !trace_do_binning">
          <span class="v-messages v-messages__message text--secondary">
            <b style="color: red !important">WARNING:</b> Trace fitting may be slow without binning.
          </span>
        </v-row>

        <v-row v-if="trace_type_selected!=='Flat' && trace_do_binning && trace_bins > 20">
          <span class="v-messages v-messages__message text--secondary">
            <b style="color: red !important">WARNING:</b> Trace fitting may be slow with a large number of bins.
          </span>
        </v-row>


        <v-row v-if="trace_type_selected!=='Flat'">
          <v-text-field
            :label="api_hints_enabled ? 'plg.trace_window = ' : 'Window Width'"
            :class="api_hints_enabled ? 'api-hint' : null"
            type="number"
            v-model.number="trace_window"
            :rules="[() => trace_window!=='' || 'This field is required',
                     () => trace_window > 0 || 'Window must be positive']"
            hint="Width in rows to consider for peak finding."
            persistent-hint
          >
          </v-text-field>
        </v-row>

        <plugin-select
          v-if="trace_type_selected!=='Flat'"
          :items="trace_peak_method_items.map(i => i.label)"
          :selected.sync="trace_peak_method_selected"
          label="Peak Method"
          api_hint="plg.trace_peak_method ="
          :api_hints_enabled="api_hints_enabled"
          hint="Method to use for identifying the peak cross-dispersion pixel in each bin"
        />
      </div>

      <v-row>
        <v-expansion-panels accordion>
          <v-expansion-panel>
            <v-expansion-panel-header v-slot="{ open }">
              <span style="padding: 6px">Export Trace</span>
            </v-expansion-panel-header>
            <v-expansion-panel-content class="plugin-expansion-panel-content">
              <plugin-add-results
                :label.sync="trace_results_label"
                :label_default="trace_results_label_default"
                :label_auto.sync="trace_results_label_auto"
                :label_invalid_msg="trace_results_label_invalid_msg"
                :label_overwrite="trace_results_label_overwrite"
                label_hint="Label for the trace"
                :add_to_viewer_items="trace_add_to_viewer_items"
                :add_to_viewer_selected.sync="trace_add_to_viewer_selected"
                action_label="Create"
                action_tooltip="Create Trace"
                :action_spinner="trace_spinner"
                add_results_api_hint="trace_results"
                action_api_hint="plg.create_trace()"
                :api_hints_enabled="api_hints_enabled"
                @click:action="create_trace"
              ></plugin-add-results>
            </v-expansion-panel-content>
          </v-expansion-panel>
        </v-expansion-panels>
      </v-row>
    </div>

    <div @mouseover="() => active_step='bg'">
      <j-plugin-section-header :active="active_step==='bg'">Background</j-plugin-section-header>
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
        api_hint="plg.bg_dataset ="
        :api_hints_enabled="api_hints_enabled"
        hint="Select the data used to determine the background."
      />

      <plugin-select
        :items="bg_type_items.map(i => i.label)"
        :selected.sync="bg_type_selected"
        label="Background Type"
        api_hint="plg.bg_type ="
        :api_hints_enabled="api_hints_enabled"
        hint="Method to use for creating background"
      />

      <plugin-dataset-select
        :items="bg_trace_items"
        :selected.sync="bg_trace_selected"
        :show_if_single_entry="false"
        label="Background Trace"
        api_hint="plg.bg_trace ="
        :api_hints_enabled="api_hints_enabled"
        hint="Trace to use as reference for background window(s).  'From Plugin' uses trace defined in Trace section above."
      />

      <v-row v-if="bg_type_selected === 'Manual'">
        <v-text-field
          :label="api_hints_enabled ? 'plg.bg_trace_pixel' : 'Pixel'"
          :class="api_hints_enabled ? 'api-hint' : null"
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
          :label="api_hints_enabled ? 'plg.bg_separation =' : 'Separation'"
          :class="api_hints_enabled ? 'api-hint' : null"
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
          :label="api_hints_enabled ? 'plg.bg_width =' : 'Width'"
          :class="api_hints_enabled ? 'api-hint' : null"
          type="number"
          v-model.number="bg_width"
          :rules="[() => bg_width!=='' || 'This field is required']"
          hint="Width of background window, in pixels."
          persistent-hint
        >
        </v-text-field>
      </v-row>

      <plugin-select
        :items="bg_statistic_items.map(i => i.label)"
        :selected.sync="bg_statistic_selected"
        label="Statistic"
        api_hint="plg.bg_statistic ="
        :api_hints_enabled="api_hints_enabled"
        hint="Statistic to use over the background window."
      />

      <v-row>
        <v-expansion-panels accordion>
          <v-expansion-panel>
            <v-expansion-panel-header v-slot="{ open }">
              <span style="padding: 6px">Export Background Image</span>
            </v-expansion-panel-header>
            <v-expansion-panel-content class="plugin-expansion-panel-content">
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
                :action_spinner="bg_img_spinner"
                add_results_api_hint="plg.bg_results"
                action_api_hint="plg.export_bg_img()"
                :api_hints_enabled="api_hints_enabled"
                @click:action="create_bg_img"
              ></plugin-add-results>
            </v-expansion-panel-content>
          </v-expansion-panel>
        </v-expansion-panels>
      </v-row>
      <v-row>
        <v-expansion-panels accordion>
          <v-expansion-panel>
            <v-expansion-panel-header v-slot="{ open }">
              <span style="padding: 6px">Export Background Spectrum</span>
            </v-expansion-panel-header>
            <v-expansion-panel-content class="plugin-expansion-panel-content">
              <plugin-add-results
                :label.sync="bg_spec_results_label"
                :label_default="bg_spec_results_label_default"
                :label_auto.sync="bg_spec_results_label_auto"
                :label_invalid_msg="bg_spec_results_label_invalid_msg"
                :label_overwrite="bg_spec_results_label_overwrite"
                label_hint="Label for the background spectrum"
                :add_to_viewer_items="bg_spec_add_to_viewer_items"
                :add_to_viewer_selected.sync="bg_spec_add_to_viewer_selected"
                action_label="Export"
                action_tooltip="Create Background Spectrum"
                add_results_api_hint="plg.bg_spec_results"
                action_api_hint="plg.export_bg_spectrum()"
                :api_hints_enabled="api_hints_enabled"
                @click:action="create_bg_spec"
              ></plugin-add-results>
            </v-expansion-panel-content>
          </v-expansion-panel>
        </v-expansion-panels>
      </v-row>
      <v-row>
        <v-expansion-panels accordion>
          <v-expansion-panel>
            <v-expansion-panel-header v-slot="{ open }">
              <span style="padding: 6px">Export Background-Subtracted Image</span>
            </v-expansion-panel-header>
            <v-expansion-panel-content class="plugin-expansion-panel-content">
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
                add_results_api_hint="plg.bg_sub_results"
                action_api_hint="plg.export_bg_sub()"
                :api_hints_enabled="api_hints_enabled"
                @click:action="create_bg_sub"
              ></plugin-add-results>
            </v-expansion-panel-content>
          </v-expansion-panel>
        </v-expansion-panels>
      </v-row>
    </div>

    <div @mouseover="() => active_step='ext'">
      <j-plugin-section-header :active="active_step==='ext'">Extraction</j-plugin-section-header>
      <v-row>
        <j-docs-link>
          Extract a 1D spectrum from a 2D spectrum.  See the <j-external-link link='https://specreduce.readthedocs.io/en/latest/#module-specreduce.extract' linktext='specreduce docs'></j-external-link> for more details on the available extraction methods.
        </j-docs-link>
      </v-row>

      <plugin-dataset-select
        :items="ext_dataset_items"
        :selected.sync="ext_dataset_selected"
        :show_if_single_entry="false"
        label="2D Spectrum"
        api_hint="plg.ext_dataset ="
        :api_hints_enabled="api_hints_enabled"
        hint="Select the data used to extract the spectrum.  'From Plugin' uses background-subtracted image defined in Background section above."
      />

      <plugin-dataset-select
        :items="ext_trace_items"
        :selected.sync="ext_trace_selected"
        :show_if_single_entry="false"
        label="Extraction Trace"
        api_hint="plg.ext_trace ="
        :api_hints_enabled="api_hints_enabled"
        hint="Trace to use as center of extraction window.  'From Plugin' uses trace defined in Trace section above."
      />

      <plugin-select
        :items="ext_type_items.map(i => i.label)"
        :selected.sync="ext_type_selected"
        label="Extraction Type"
        api_hint="plg.ext_type ="
        :api_hints_enabled="api_hints_enabled"
        hint="Method to use for extracting the spectrum."
      />

      <v-row v-if="ext_uncert_warn">
        <span class="v-messages v-messages__message text--secondary">
          <b style="color: red !important">WARNING:</b> uncertainties on input 2D spectrum have unclear units; assuming standard deviation.
        </span>
      </v-row>

      <v-row v-if="ext_type_selected === 'Boxcar'">
        <v-text-field
          :label="api_hints_enabled ? 'plg.ext_width =' : 'Width'"
          :class="api_hints_enabled ? 'api-hint' : null"
          type="number"
          v-model.number="ext_width"
          :rules="[() => ext_width!=='' || 'This field is required']"
          hint="Width of extraction window, in pixels."
          persistent-hint
        >
        </v-text-field>
      </v-row>

      <plugin-select
        v-if="ext_type_selected === 'Horne'"
        :items=" horne_ext_profile_items.map(i => i.label)"
        :selected.sync="horne_ext_profile_selected"
        label="Profile Type"
        api_hint="plg.horne_ext_profile ="
        :api_hints_enabled="api_hints_enabled"
        hint="Profile to use for Horne extraction."
      />

      <v-row v-if="horne_ext_profile_selected === 'Self (interpolated)'">
        <v-text-field
          :label="api_hints_enabled ? 'plg.self_prof_n_bins =' : 'N Bins'"
          :class="api_hints_enabled ? 'api-hint' : null"
          type="number"
          v-model.number=self_prof_n_bins
          :rules="[() => self_prof_n_bins !== '' || 'This field is required',
                   () => self_prof_n_bins >0 || 'Number of bins must be greater than zero']"
          hint="Number of bins used to measure self profile."
          persistent-hint
        >
        </v-text-field>
      </v-row>

      <div v-if="ext_type_selected === 'Horne'">
        <v-row v-if="horne_ext_profile_selected === 'Self (interpolated)'">
          <v-text-field
            :label="api_hints_enabled ? 'plg.self_prof_interp_degree_x =' : 'Interpolation Degree (X)'"
            :class="api_hints_enabled ? 'api-hint' : null"
            type="number"
            v-model.number=self_prof_interp_degree_x
            :rules="[() => self_prof_interp_degree_x !== '' || 'This field is required',
                     () => self_prof_interp_degree_x >0 || 'X interpolation degree must be be greater than zero']"
            hint="Interpolation degree (X) to measure self profile."
            persistent-hint
          >
          </v-text-field>
        </v-row>

        <v-row v-if="horne_ext_profile_selected === 'Self (interpolated)'">
          <v-text-field
            :label="api_hints_enabled ? 'plg.self_prof_interp_degree_y =' : 'Interpolation Degree (Y)'"
            :class="api_hints_enabled ? 'api-hint' : null"
            type="number"
            v-model.number=self_prof_interp_degree_y
            :rules="[() => self_prof_interp_degree_y !== '' || 'This field is required',
                     () => self_prof_interp_degree_y >0 || 'Y interpolation degree must be be greater than zero']"
            hint="Interpolation degree (Y) to measure self profile."
            persistent-hint
          >
          </v-text-field>
        </v-row>
      </div>

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
        :action_disabled="ext_specreduce_err.length > 0"
        :action_spinner="spinner"
        add_results_api_hint="plg.ext_results"
        action_api_hint="plg.export_extract_spectrum()"
        :api_hints_enabled="api_hints_enabled"
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
