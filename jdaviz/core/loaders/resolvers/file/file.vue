<template>
  <j-loader
    title="Load Local File"
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
    :server_is_remote="server_is_remote"
    :is_wcs_linked="is_wcs_linked"
    :image_data_loaded="image_data_loaded"
    :footprint_select_icon="footprint_select_icon"
    :custom_toolbar_enabled="custom_toolbar_enabled"
  >
    <v-row style="padding-left: 12px; margin-bottom: 16px">
      Select a file with data you want to load into this instance of Jdaviz.
    </v-row>
    <v-row v-if="api_hints_enabled">
      <span class="api-hint">
        ldr.filepath = '{{ filepath }}'
      </span>
    </v-row>
    <jupyter-widget :widget="file_chooser_widget"></jupyter-widget>
  </j-loader>
</template>