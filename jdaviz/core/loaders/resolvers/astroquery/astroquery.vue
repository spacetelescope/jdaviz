<template>
  <j-loader
    title="Astroquery"
    :popout_button="popout_button"
    :spinner="spinner"
    :parsed_input_is_empty="parsed_input_is_empty"
    :parsed_input_is_resolvable="parsed_input_is_resolvable"
    :parsed_input_is_query="parsed_input_is_query"
    :treat_table_as_query.sync="treat_table_as_query"
    :limit_to_science_products.sync="limit_to_science_products"
    :can_filter_science.sync="can_filter_science"
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
    :server_is_remote="server_is_remote"
    :is_wcs_linked="is_wcs_linked"
    :footprint_select_icon="footprint_select_icon"
    :custom_toolbar_enabled="custom_toolbar_enabled"
    :image_data_loaded="image_data_loaded"
    @link-by-wcs="link_by_wcs"
    @toggle-custom-toolbar="toggle_custom_toolbar"
  >
    <v-form v-model="all_fields_filled">
      <j-plugin-section-header>Source Selection</j-plugin-section-header>

      <plugin-select
        :items="input_items"
        :selected.sync="input_selected"
        label="Input"
        api_hint="ldr.input_select ="
        :api_hints_enabled="api_hints_enabled"
        hint="Select the source of cone-search coordinates"
      ></plugin-select>

      <!-- Source mode -->
      <div v-if="input_selected === 'Source'">
        <v-row>
          <v-text-field
            v-model="source"
            :label="api_hints_enabled ? 'ldr.source =' : 'Source/Coordinates'"
            :class="api_hints_enabled ? 'api-hint' : null"
            hint="Enter a source name or coordinates in degrees to center your query on"
            :rules="[() => !!source || 'This field is required']"
            :error-messages="parsed_input_is_resolvable ? [parsed_input_is_resolvable] : []"
            persistent-hint>
          </v-text-field>
        </v-row>

        <plugin-select
          :items="coordframe_choices.map(i => i.label)"
          :selected.sync="coordframe_selected"
          label="Coordinate Frame"
          api_hint="ldr.coordframe ="
          :api_hints_enabled="api_hints_enabled"
          hint="Astronomical Coordinate Frame of the provided Coordinates"
        ></plugin-select>
      </div>

      <!-- Viewer mode -->
      <div v-if="input_selected === 'Viewer'">
        <plugin-viewer-select
          :items="viewer_items"
          :selected.sync="viewer_selected"
          :show_if_single_entry="false"
          label="Viewer"
          api_hint="ldr.viewer ="
          :api_hints_enabled="api_hints_enabled"
          hint="Select a viewer to retrieve center coordinates."
        />

        <v-row>
          <v-switch
            v-model="coord_follow_viewer_pan"
            label="Follow Viewer Center"
            hint="Automatically adjust coordinates as viewer pans and zooms"
            persistent-hint
          ></v-switch>
        </v-row>

        <v-row>
          <div :style="!coord_follow_viewer_pan ? 'width: 100%' : 'width: calc(100% - 32px)'">
            <v-text-field
              v-model="source"
              :label="api_hints_enabled ? 'ldr.source =' : 'Viewer Center'"
              :class="api_hints_enabled ? 'api-hint' : null"
              hint="Current viewer center coordinates"
              :disabled="true"
              persistent-hint>
            </v-text-field>
          </div>
          <div v-if="!coord_follow_viewer_pan" style="line-height:64px; width:32px">
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
          :disabled="true"
        ></plugin-select>
      </div>

      <!-- Catalog mode -->
      <div v-if="input_selected === 'Catalog'">
        <plugin-dataset-select
          :items="catalog_items"
          :selected.sync="catalog_selected"
          label="Catalog"
          api_hint="ldr.catalog ="
          :api_hints_enabled="api_hints_enabled"
          hint="Select a catalog from the data collection"
        />

        <plugin-select
          :items="catalog_subset_items"
          :selected.sync="catalog_subset_selected"
          label="Subset"
          api_hint="ldr.catalog_subset ="
          :api_hints_enabled="api_hints_enabled"
          hint="Optionally restrict query to a subset of catalog rows"
        ></plugin-select>

        <v-row>
          <v-radio-group
            v-model="catalog_col_type"
            row
            label="Column Type"
            style="margin-top: 0"
          >
            <v-radio label="Sky Coordinates" value="sky_coords"></v-radio>
            <v-radio label="Source Names" value="source_name"></v-radio>
          </v-radio-group>
        </v-row>

        <v-row v-if="catalog_col_type === 'source_name'">
          <v-alert type="warning" dense>
            Source name resolution requires one HTTP request per catalog row (Sesame/CDS).
            Large catalogs may take significant time.
          </v-alert>
        </v-row>
      </div>

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

      <j-plugin-section-header>Telescope/Mission</j-plugin-section-header>

      <plugin-select
        :show_if_single_entry="true"
        :items="telescope_items.map(i => i.label)"
        :selected.sync="telescope_selected"
        label="Telescope"
        :search="true"
        api_hint="ldr.telescope ="
        :api_hints_enabled="api_hints_enabled"
        hint="Select a telescope to search for data"
      ></plugin-select>

      <v-row justify="space-between" style="margin-top: 12px">
        <v-text-field
          v-model.number='max_results'
          type="number"
          style="padding: 0px"
          :label="api_hints_enabled ? 'ldr.max_results =' : 'Max Results'"
          :class="api_hints_enabled ? 'api-hint' : null"
          persistent-hint
          hint="Maximum number of results to return from the query"
        ></v-text-field>
      </v-row>
    </v-form>



    <v-row class="row-no-outside-padding" justify="end" style="margin-top: 32px">
      <span v-if="query_progress" style="align-self: center; margin-right: 8px; font-size: 0.85em; color: gray;">
        {{ query_progress }}
      </span>
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

    <v-row v-if="returned_no_results">
      <v-alert type="warning">
        The search returned no results. Please modify your query parameters and try again.
      </v-alert>
    </v-row>

    <v-row v-if="returned_max_results">
      <v-alert type="warning">
        The number of results returned has reached the maximum limit set ({{ max_results }}). Consider increasing the maximum results to ensure all data is retrieved.
      </v-alert>
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
