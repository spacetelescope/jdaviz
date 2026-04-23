<template>
  <j-tray-plugin
    :description="docs_description"
    :link="docs_link || 'https://jdaviz.readthedocs.io/en/'+vdocs+'/'+config+'/plugins.html#catalog-search'"
    :uses_active_status="uses_active_status"
    v-model:api_hints_enabled="api_hints_enabled"
    @plugin-ping="plugin_ping($event)"
    :keep_active_sync="keep_active"
    :popout_button="popout_button"
    v-model:scroll_to="scroll_to">

    <v-alert type="warning">
      This plugin will be deprecated in a future version of Jdaviz. Please see
      <a href="https://jdaviz.readthedocs.io/en/latest/plugins/catalog_search.html">the docs</a>
      for more information.
    </v-alert>

    <plugin-viewer-select
       :items="viewer_items"
       v-model:selected="viewer_selected"
       label="Viewer"
       :show_if_single_entry="false"
       hint="Select a viewer to search."
    />

    <plugin-file-import-select
      :items="catalog_items"
      v-model:selected="catalog_selected"
      label="Catalog"
      hint="Select a catalog to search."
      api_hint="plg.catalog ="
      :api_hints_enabled="api_hints_enabled"
      v-model:from_file="from_file"
      :from_file_message="from_file_message"
      dialog_title="Import Catalog"
      dialog_hint="Select a file containing a catalog"
      @click-cancel="file_import_cancel()"
      @click-import="file_import_accept()"
    >
      <g-file-import id="file-uploader"></g-file-import>
    </plugin-file-import-select>

    <j-flex-row v-if="catalog_selected === 'Gaia'">
      <j-docs-link>
        See the <j-external-link link='https://astroquery.readthedocs.io/en/latest/gaia/gaia.html' linktext='astropy.gaia docs'></j-external-link> for details on the query defaults.
      </j-docs-link>
    </j-flex-row>

    <j-flex-row v-if="catalog_selected && catalog_selected.endsWith('.ecsv')">
      <v-select
        v-model="selected_columns"
        :items="column_names"
        label="Select Columns"
        multiple
        hint="Select columns to display in the table."
      />
    </j-flex-row>

    <j-flex-row>
      <v-text-field
        v-model.number="max_sources"
        type="number"
        step="10"
        :rules="[
          () => max_sources!=='' || 'This field is required',
          max_sources => max_sources > 0 || 'Max sources must be a postive integer.',
          ]"
        label="Max sources"
        hint="Maximum number of sources."
        persistent-hint
        :label="api_hints_enabled ? 'plg.max_sources =' : 'Max Sources'"
        :class="api_hints_enabled ? 'api-hint' : null"
      ></v-text-field>
    </j-flex-row>

    <v-row class="row-no-outside-padding vuetify2">
       <v-col>
         <plugin-action-button
            :results_isolated_to_plugin="true"
            @click="do_search"
            :spinner="spinner"
            :api_hints_enabled="api_hints_enabled"
          >
            {{ api_hints_enabled ?
              'plg.search()'
              :
              'Search'
            }}
          </plugin-action-button>
       </v-col>
    </v-row>

    <j-flex-row>
       <p class="font-weight-bold">Results:</p>
       <span style='padding-left: 4px' v-if="results_available">{{number_of_results}}</span>
    </j-flex-row>

    <j-custom-toolbar-toggle
      v-if="number_of_results > 0"
      :enabled="custom_toolbar_enabled"
      text="catalog selection tools"
      @toggle-custom-toolbar="toggle_custom_toolbar"
    >
      <v-icon>mdi-crosshairs-gps</v-icon>
    </j-custom-toolbar-toggle>

    <jupyter-widget v-if="table_selected_widget" :widget="table_selected_widget" :key="table_selected_widget"></jupyter-widget>
    <v-row class="vuetify2" v-if="row_selected_count > 0">
        <v-col>
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
        </v-col>
    </v-row>

    <jupyter-widget v-if="table_widget" :widget="table_widget" :key="table_widget"></jupyter-widget>

  </j-tray-plugin>
</template>
