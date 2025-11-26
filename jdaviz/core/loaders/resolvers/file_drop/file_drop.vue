<template>
  <j-loader
    title="File Drop"
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
    :server_is_remote="server_is_remote"
    :is_wcs_linked="is_wcs_linked"
    :image_data_loaded="image_data_loaded"
    :footprint_select_icon="footprint_select_icon"
    :custom_toolbar_enabled="custom_toolbar_enabled"
  >
    <v-row>
      Select a file from your local file system and send to jdaviz through the browser.
    </v-row>
    <v-alert v-if="api_hints_enabled" type="info">
      Use UI to select file (no API access available).
    </v-alert>
    <jupyter-widget :widget="file_drop_widget"></jupyter-widget>
    <v-progress-linear v-if="progress !== 100" :value="progress"></v-progress-linear>
    <v-alert v-if="nfiles > 1" type="warning">
      Multiple files dropped, only using first entry.
    </v-alert>

  </j-loader>
</template>