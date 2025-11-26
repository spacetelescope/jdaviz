<template>
  <j-loader
    title="Virtual Observatory"
    :popout_button="popout_button"
    :spinner="spinner"
    :parsed_input_is_empty="parsed_input_is_empty"
    :parsed_input_is_query="parsed_input_is_query"
    :treat_table_as_query.sync="treat_table_as_query"
    :observation_table="observation_table"
    :observation_table_populated="observation_table_populated"
    :file_table="file_table"
    :file_table_populated="file_table_populated"
    :file_cache="file_cache"
    :file_timeout="file_timeout"
    :target_items="target_items"
    :target_selected.sync="target_selected"
    :format_items="format_items"
    :format_selected.sync="format_selected"
    :importer_widget="importer_widget"
    :api_hints_enabled="api_hints_enabled"
    :valid_import_formats="valid_import_formats"
    :is_wcs_linked="is_wcs_linked"
    :image_data_loaded="image_data_loaded"
    :footprint_select_icon="footprint_select_icon"
    :custom_toolbar_enabled="custom_toolbar_enabled"
  >
    <v-form v-model="all_fields_filled">
      <j-plugin-section-header>Source Selection</j-plugin-section-header>

      <plugin-viewer-select
        :items="viewer_items"
        :selected.sync="viewer_selected"
        :show_if_single_entry="false"
        label="Viewer"
        api_hint="ldr.viewer ="
        :api_hints_enabled="api_hints_enabled"
        hint="Select a viewer to retrieve center coordinates, or Manual for manual coordinate entry."
      />

      <v-row v-if="viewer_selected !== 'Manual'">
        <v-switch
          v-model="coord_follow_viewer_pan"
          label="Follow Viewer Center"
          hint="Automatically adjust coordinates as viewer pans and zooms"
          persistent-hint
        ></v-switch>
      </v-row>

      <v-row>
        <div :style="!(viewer_selected !== 'Manual' && !coord_follow_viewer_pan) ? 'width: 100%' : 'width: calc(100% - 32px)'">
          <v-text-field
            v-model="source"
            :label="api_hints_enabled ? 'ldr.source =' : 'Source/Coordinates'"
            :class="api_hints_enabled ? 'api-hint' : null"
            hint="Enter a source name or coordinates in degrees to center your query on"
            :disabled="viewer_selected !== 'Manual'"
            :rules="[() => !!source || 'This field is required']"
            persistent-hint>
          </v-text-field>
        </div>
        <div v-if="viewer_selected !== 'Manual' && !coord_follow_viewer_pan" style="line-height:64px; width:32px">
          <j-tooltip :tipid="viewer_centered ? 'plugin-vo-autocenter-centered' : 'plugin-vo-autocenter-not-centered'">
            <v-btn
              id="autocenterbtn"
              @click="center_on_data"
              :disabled="viewer_centered"
              icon>
              <v-icon>
                {{ viewer_centered ? 'mdi-crosshairs-gps' : 'mdi-crosshairs' }}
              </v-icon>
            </v-btn>
          </j-tooltip>
        </div>
      </v-row>

      <plugin-select
        :items="coordframe_choices.map(i => i.label)"
        :selected.sync="coordframe_selected"
        label="Coordinate Frame"
        api_hint="ldr.coordframe ="
        :api_hints_enabled="api_hints_enabled"
        hint="Astronomical Coordinate Frame of the provided Coordinates"
        :disabled="viewer_selected !== 'Manual'"
      ></plugin-select>

      <v-row justify="space-between">
        <div :style="{ width: '55%' }">
          <v-text-field
            v-model.number="radius"
            type="number"
            :label="api_hints_enabled ? 'ldr.radius =' : 'Radius'"
            :class="api_hints_enabled ? 'api-hint' : null"
            hint="Angular radius around source coordinates, within which to query for data (Default 1 degree)"
            persistent-hint>
          </v-text-field>
        </div>
        <div :style="{ width: '40%' }">
          <plugin-select
            :items="radius_unit_items.map(i => i.label)"
            :selected.sync="radius_unit_selected"
            label="Unit"
            api_hint="ldr.radius_unit ="
            :api_hints_enabled="api_hints_enabled"
          ></plugin-select>
        </div>
      </v-row>

      <j-plugin-section-header>Survey Collections</j-plugin-section-header>
      <v-row>
        <j-tooltip tipid='plugin-vo-filter-coverage'>
          <plugin-switch
            :value.sync="resource_filter_coverage"
            label="Filter by Coverage"
            api_hint="ldr.resource_filter_coverage ="
            :api_hints_enabled="api_hints_enabled"
          ></plugin-switch>
        </j-tooltip>
      </v-row>

      <plugin-select
        :show_if_single_entry="true"
        :items="waveband_items.map(i => i.label)"
        :selected.sync="waveband_selected"
        label="Resource Waveband"
        :search="true"
        api_hint="ldr.waveband ="
        :api_hints_enabled="api_hints_enabled"
        hint="Select a spectral waveband to filter your surveys"
      ></plugin-select>


      <plugin-select
        :show_if_single_entry="true"
        :items="resource_items.map(i => i.label)"
        :selected.sync="resource_selected"
        :loading="resources_loading"
        :rules="[() => !!resource_selected || 'This field is required']"
        label="Available Resources"
        :search="true"
        api_hint="ldr.resource ="
        :api_hints_enabled="api_hints_enabled"
        hint="Select a SIA resource to query"
      ></plugin-select>
    </v-form>

    <v-row class="row-no-outside-padding" justify="end">
      <plugin-action-button
        :spinner="results_loading"
        :disabled="!all_fields_filled"
        :results_isolated_to_plugin="true"
        :api_hints_enabled="api_hints_enabled"
        @click="query_archive">
          {{ api_hints_enabled ?
              'ldr.query_archive()'
              :
              'Query Archive'
          }}
      </plugin-action-button>
    </v-row>
  </j-loader>
</template>

<script>
export default {
  data() {
    return {
      all_fields_filled: false, // Reactive property for form validity
    };
  },
};
</script>
