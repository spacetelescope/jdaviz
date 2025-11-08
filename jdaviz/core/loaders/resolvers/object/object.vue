<template>
  <j-loader
    title="Python Object (from API)"
    :popout_button="popout_button"
    :spinner="spinner"
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
  >
    <v-alert v-if="!is_wcs_linked" type="warning" dense style="margin-bottom: 12px">
      <v-row no-gutters align="center">
        <v-col>
          <strong>Images are not linked by WCS.</strong> Link images to view footprints properly.
        </v-col>
        <v-col cols="auto" style="margin-left: 8px;">
          <v-btn small color="primary" @click="link_by_wcs">
            Link by WCS
          </v-btn>
        </v-col>
      </v-row>
    </v-alert>

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