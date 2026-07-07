<template>
  <j-loader
    title="Astroquery"
    :popout_button="popout_button"
    :spinner="spinner"
    :spinner_success_message="spinner_success_message"
    :parsed_input_is_empty="parsed_input_is_empty"
    :parsed_input_is_query="parsed_input_is_query"
    v-model:treat_table_as_query="treat_table_as_query"
    v-model:limit_to_science_products="limit_to_science_products"
    v-model:can_filter_science="can_filter_science"
    :observation_table="observation_table"
    :observation_table_populated="observation_table_populated"
    :file_table="file_table"
    :file_table_populated="file_table_populated"
    :file_cache="file_cache"
    :file_timeout="file_timeout"
    :target_items="target_items"
    v-model:target_selected="target_selected"
    :format_items="format_items"
    v-model:format_selected="format_selected"
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
        :items="input_items.map(i => i.label)"
        v-model:selected="input_selected"
        label="Input"
        api_hint="ldr.input_select ="
        :api_hints_enabled="api_hints_enabled"
        hint="Select the source of cone-search coordinates."
      ></plugin-select>

      <!-- Source mode -->
      <div v-if="input_selected === 'Source'">
        <j-flex-row>
          <v-text-field
            v-model="source"
            :label="api_hints_enabled ? 'ldr.source =' : 'Source/Coordinates'"
            :class="api_hints_enabled ? 'api-hint' : null"
            hint="Enter a source name or coordinates in degrees to center your query on"
            :rules="[() => !!source || 'This field is required']"
            persistent-hint>
          </v-text-field>
        </j-flex-row>

        <plugin-select
          :items="coordframe_choices.map(i => i.label)"
          v-model:selected="coordframe_selected"
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
          v-model:selected="viewer_selected"
          :show_if_single_entry="false"
          label="Viewer"
          api_hint="ldr.viewer ="
          :api_hints_enabled="api_hints_enabled"
          hint="Select a viewer to retrieve center coordinates."
        />

        <div style="display: flex; flex-direction: column; gap: 2px; padding-top: 4px; padding-bottom: 4px">
          <div style="display: grid; grid-template-columns: auto 1fr; align-items: center; column-gap: 8px">
            <v-switch
              v-model="coord_follow_viewer_pan"
              hide-details
              density="compact"
            ></v-switch>
            <span style="font-size: 1rem; font-weight: 500; padding-left: 8px">Follow Viewer Center</span>
            <div></div>
            <span class="text-medium-emphasis" style="font-size: 0.875rem; margin-top: -6px; padding-left: 8px">{{ source }}</span>
          </div>
          <div class="text-medium-emphasis" style="font-size: 0.75rem; margin-top: 2px">
            Automatically adjust coordinates as viewer pans and zooms
          </div>
        </div>

        <plugin-select
          :items="coordframe_choices.map(i => i.label)"
          v-model:selected="coordframe_selected"
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
          v-model:selected="catalog_selected"
          label="Catalog"
          api_hint="ldr.catalog ="
          :api_hints_enabled="api_hints_enabled"
          hint="Select a loaded catalog; the archive is queried once per catalog row."
        />

        <plugin-select
          :items="catalog_subset_items.map(i => i.label)"
          v-model:selected="catalog_subset_selected"
          label="Subset"
          api_hint="ldr.catalog_subset ="
          :api_hints_enabled="api_hints_enabled"
          hint="Optionally restrict the query to a subset of catalog rows."
        ></plugin-select>

        <j-flex-row>
          <v-radio-group
            v-model="catalog_col_type"
            row
            label="Coordinates from"
            style="margin-top: 0"
          >
            <v-radio label="RA/Dec Columns" value="sky_coords"></v-radio>
            <v-radio label="Source Names" value="source_name"></v-radio>
          </v-radio-group>
        </j-flex-row>

        <plugin-select
          v-if="catalog_col_type === 'source_name'"
          :items="catalog_name_col_items.map(i => i.label)"
          v-model:selected="catalog_name_col_selected"
          label="Source Name Column"
          api_hint="ldr.catalog_name_col ="
          :api_hints_enabled="api_hints_enabled"
          hint="Column of source names to resolve into coordinates."
        ></plugin-select>

        <j-flex-row v-if="catalog_col_type === 'source_name'">
          <v-alert type="warning" dense>
            Source-name resolution issues one request per catalog row (Sesame/CDS).
            Large catalogs may take significant time.
          </v-alert>
        </j-flex-row>

        <plugin-select
          :items="coordframe_choices.map(i => i.label)"
          v-model:selected="coordframe_selected"
          label="Coordinate Frame"
          api_hint="ldr.coordframe ="
          :api_hints_enabled="api_hints_enabled"
          hint="Astronomical Coordinate Frame of the catalog coordinates"
        ></plugin-select>
      </div>

      <j-flex-row justify="space-between">
        <div :style="{ width: '55%' }">
          <v-text-field
            v-model.number="radius"
            type="number"
            :label="api_hints_enabled ? 'ldr.radius =' : 'Radius'"
            :class="api_hints_enabled ? 'api-hint' : null">
          </v-text-field>
        </div>
        <div :style="{ width: '40%' }">
          <plugin-select
            :items="radius_unit_items.map(i => i.label)"
            v-model:selected="radius_unit_selected"
            label="Unit"
            api_hint="ldr.radius_unit ="
            :api_hints_enabled="api_hints_enabled"
          ></plugin-select>
        </div>
      </j-flex-row>
      <j-flex-row>
        <span class="v-messages" style="width: 100%; padding: 0 12px; margin-top: -12px">
          Angular radius around source coordinates, within which to query for data (Default 1 degree)
        </span>
      </j-flex-row>

      <j-plugin-section-header>Telescope/Mission</j-plugin-section-header>

      <plugin-select
        :show_if_single_entry="true"
        :items="telescope_items.map(i => i.label)"
        v-model:selected="telescope_selected"
        label="Telescope"
        :search="true"
        api_hint="ldr.telescope ="
        :api_hints_enabled="api_hints_enabled"
        hint="Select a telescope to search for data"
      ></plugin-select>

      <j-flex-row justify="space-between" style="margin-top: 12px">
        <v-text-field
          v-model.number='max_results'
          type="number"
          style="padding: 0px"
          :label="api_hints_enabled ? 'ldr.max_results =' : 'Max Results'"
          :class="api_hints_enabled ? 'api-hint' : null"
          persistent-hint
          hint="Maximum number of results to return from the query"
        ></v-text-field>
      </j-flex-row>
    </v-form>



    <j-flex-row class="row-no-outside-padding" justify="end" style="margin-top: 32px">
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
    </j-flex-row>

    <j-flex-row v-if="returned_no_results">
      <v-alert type="warning">
        The search returned no results. Please modify your query parameters and try again.
      </v-alert>
    </j-flex-row>

    <j-flex-row v-if="returned_max_results">
      <v-alert type="warning">
        The number of results returned has reached the maximum limit set ({{ max_results }}). Consider increasing the maximum results to ensure all data is retrieved.
      </v-alert>
    </j-flex-row>
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
