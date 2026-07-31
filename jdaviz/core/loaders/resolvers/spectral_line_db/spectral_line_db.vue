<template>
  <j-loader
    :title="title"
    :popout_button="popout_button"
    :spinner="spinner"
    :spinner_success_message="spinner_success_message"
    :parsed_input_is_empty="parsed_input_is_empty"
    :parsed_input_not_resolvable_message="parsed_input_not_resolvable_message"
    :parsed_input_is_query="parsed_input_is_query"
    v-model:treat_table_as_query="treat_table_as_query"
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
    :server_is_remote="server_is_remote"
    :hide_resolver="hide_resolver"
    :hide_resolver_inputs="hide_resolver_inputs"
    :is_wcs_linked="is_wcs_linked"
    :footprint_select_icon="footprint_select_icon"
    :custom_toolbar_enabled="custom_toolbar_enabled"
    :image_data_loaded="image_data_loaded"
    @link-by-wcs="link_by_wcs"
    @toggle-custom-toolbar="toggle_custom_toolbar"
  >

    <j-plugin-section-header>Query Database</j-plugin-section-header>

    <j-flex-row justify="space-between">
      <div style="width: 35%">
        <v-text-field
          v-model="wavelength_min"
          :label="api_hints_enabled ? 'ldr.wavelength_min =' : 'Min'"
          :class="api_hints_enabled ? 'api-hint' : null"
          placeholder="e.g. 6000"
          type="number"
          dense
        ></v-text-field>
      </div>
      <div style="width: 35%">
        <v-text-field
          v-model="wavelength_max"
          :label="api_hints_enabled ? 'ldr.wavelength_max =' : 'Max'"
          :class="api_hints_enabled ? 'api-hint' : null"
          placeholder="e.g. 7000"
          type="number"
          dense
        ></v-text-field>
      </div>
      <div style="width: 28%">
        <plugin-select
          :items="wavelength_unit_items"
          v-model:selected="wavelength_unit_selected"
          label="Unit"
          api_hint="ldr.wavelength_unit ="
          :api_hints_enabled="api_hints_enabled"
          :show_if_single_entry="true"
        ></plugin-select>
      </div>
    </j-flex-row>

    <plugin-select
      :items="element_items"
      v-model:selected="element_selected"
      label="Element / Molecule"
      api_hint="ldr.element ="
      :api_hints_enabled="api_hints_enabled"
      :show_if_single_entry="true"
      :search="true"
      hint="Filter by element or molecule tag"
    ></plugin-select>

    <j-flex-row>
      <v-text-field
        v-model="name_contains"
        :label="api_hints_enabled ? 'ldr.name_contains =' : 'Line name contains'"
        :class="api_hints_enabled ? 'api-hint' : null"
        dense
        clearable
        hint="Case-insensitive substring match on line name"
        persistent-hint
      ></v-text-field>
    </j-flex-row>

    <j-flex-row class="row-no-outside-padding" justify="end" style="margin-top: 8px">
      <span
        v-if="search_status"
        style="align-self: center; margin-right: 8px; font-size: 0.85em; color: gray;"
      >
        {{ search_status }}
      </span>
      <plugin-action-button
        :spinner="search_results_loading"
        :results_isolated_to_plugin="true"
        :api_hints_enabled="api_hints_enabled"
        @click="search"
      >
        {{ api_hints_enabled ? 'ldr.search()' : 'Search' }}
      </plugin-action-button>
    </j-flex-row>

    <div v-if="search_results.length > 0" style="margin-top: 8px">
      <j-plugin-section-header>Search Results</j-plugin-section-header>
      <div style="max-height: 240px; overflow-y: auto; margin: 0 -12px">
        <v-simple-table dense class="spectral-line-db-table">
          <thead>
            <th class="text-left">Line</th>
            <th class="text-left">λ<sub>rest</sub></th>
            <th class="text-left">Unit</th>
            <th class="text-left">Element</th>
            <th></th>
          </thead>
          <tbody>
            <tr v-for="(row, i) in search_results" :key="i">
              <td style="font-size: 0.85em">{{ row.line_name }}</td>
              <td style="font-size: 0.85em">{{ row.rest_wavelength.toFixed(4) }}</td>
              <td style="font-size: 0.85em">{{ row.wavelength_unit }}</td>
              <td style="font-size: 0.85em">{{ row.element }}</td>
              <td style="text-align: right; padding-right: 4px">
                <span
                  v-if="api_hints_enabled"
                  class="api-hint"
                  style="font-size: 0.75em; margin-right: 4px; white-space: nowrap"
                >
                  {{ staged_line_names.has(row.line_name)
                      ? "ldr.unstage_line('" + row.line_name + "')"
                      : "ldr.stage_line('" + row.line_name + "')" }}
                </span>
                <v-btn
                  icon
                  x-small
                  variant="text"
                  :color="staged_line_names.has(row.line_name) ? 'error' : 'primary'"
                  @click="staged_line_names.has(row.line_name) ? unstage_line(row) : stage_line(row)"
                >
                  <v-icon>
                    {{ staged_line_names.has(row.line_name) ? 'mdi-minus-circle' : 'mdi-plus-circle' }}
                  </v-icon>
                </v-btn>
              </td>
            </tr>
          </tbody>
        </v-simple-table>
      </div>
    </div>

    <div v-if="staged_lines.length > 0" style="margin-top: 12px">
      <j-plugin-section-header style="flex: 1">
        Staged Lines ({{ staged_lines.length }})
      </j-plugin-section-header>

      <div style="max-height: 240px; overflow-y: auto; margin: 0 -12px">
        <v-simple-table dense class="spectral-line-db-table">
          <thead>
            <th class="text-left">Line</th>
            <th class="text-left">λ<sub>rest</sub></th>
            <th class="text-left">Unit</th>
            <th class="text-left">Element</th>
            <th></th>
          </thead>
          <tbody>
            <tr v-for="(row, i) in staged_lines" :key="i">
              <td style="font-size: 0.85em">{{ row.line_name }}</td>
              <td style="font-size: 0.85em">{{ row.rest_wavelength.toFixed(4) }}</td>
              <td style="font-size: 0.85em">{{ row.wavelength_unit }}</td>
              <td style="font-size: 0.85em">{{ row.element }}</td>
              <td style="text-align: right; padding-right: 4px">
                <span
                  v-if="api_hints_enabled"
                  class="api-hint"
                  style="font-size: 0.75em; margin-right: 4px; white-space: nowrap"
                >ldr.unstage_line('{{ row.line_name }}')</span>
                <v-btn
                  icon
                  x-small
                  variant="text"
                  color="error"
                  @click="unstage_line(row)"
                >
                  <v-icon>mdi-minus-circle</v-icon>
                </v-btn>
              </td>
            </tr>
          </tbody>
        </v-simple-table>
      </div>
      <j-flex-row justify="end" no-gutters>
        <j-tooltip tooltipcontent="Remove all staged lines from the list">
          <plugin-action-button
            :results_isolated_to_plugin="true"
            :api_hints_enabled="api_hints_enabled"
            @click="clear_staged"
          >
            {{ api_hints_enabled ? 'ldr.clear_staged()' : 'Clear all' }}
          </plugin-action-button>
        </j-tooltip>
      </j-flex-row>
    </div>

  </j-loader>
</template>

<style>
.spectral-line-db-table .v-data-table__wrapper > table {
  width: 100%;
}
</style>

<script>
export default {
  computed: {
    staged_line_names() {
      return new Set(this.staged_lines.map(r => r.line_name));
    }
  }
};
</script>
