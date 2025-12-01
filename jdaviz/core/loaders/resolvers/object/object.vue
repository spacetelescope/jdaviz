<template>
  <j-loader
    title="Python Object (from API)"
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
    :footprint_select_icon="footprint_select_icon"
    :custom_toolbar_enabled="custom_toolbar_enabled"
    :image_data_loaded="image_data_loaded"
    @link-by-wcs="link_by_wcs"
    @toggle-custom-toolbar="toggle_custom_toolbar"
  >
    <v-alert type="info">
      Access the user API in a notebook cell to import a python object.
    </v-alert>
    <v-text-field
      v-model='object_repr'
      prepend-icon='mdi-language-python'
      style="padding: 0px 8px"
      :disabled="true"
      label="ldr.object ="
      class="api-hint"
    ></v-text-field>
  </j-loader>
</template>