<template>
  <j-tray-plugin
    :description="docs_description"
    :link="docs_link || 'https://jdaviz.readthedocs.io/en/'+vdocs+'/'+config+'/plugins.html#catalog-search'"
    :uses_active_status="uses_active_status"
    :api_hints_enabled.sync="api_hints_enabled"
    @plugin-ping="plugin_ping($event)"
    :keep_active_sync="keep_active"
    :popout_button="popout_button"
    :scroll_to.sync="scroll_to">

    <plugin-loaders-panel
      :loader_panel_ind.sync="loader_panel_ind"
      :loader_items="loader_items"
      :loader_selected.sync="loader_selected"
      :api_hints_enabled="api_hints_enabled"
    ></plugin-loaders-panel>

    <plugin-dataset-select
      :items="dataset_items"
      :selected.sync="dataset_selected"
      :show_if_single_entry="true"
      label="Data"
      api_hint="plg.dataset ="
      :api_hints_enabled="api_hints_enabled"
      hint="Select the data set."
    />

    <jupyter-widget :widget="table_selected_widget"></jupyter-widget>

    <jupyter-widget :widget="table_widget"></jupyter-widget>

    <v-row justify='end'>
      <plugin-action-button
        :results_isolated_to_plugin="true"
        @click="zoom_in"
        :api_hints_enabled="api_hints_enabled"
      >
        {{ api_hints_enabled ?
          'plg.zoom_to_selected()'
          :
          'Zoom to Selected'
        }}
      </plugin-action-button>
    </v-row>

  </j-tray-plugin>
</template>