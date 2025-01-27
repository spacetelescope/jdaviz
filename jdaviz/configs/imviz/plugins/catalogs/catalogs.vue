<template>
  <j-tray-plugin
    :description="docs_description"
    :link="docs_link || 'https://jdaviz.readthedocs.io/en/'+vdocs+'/'+config+'/plugins.html#catalog-search'"
    :uses_active_status="uses_active_status"
    @plugin-ping="plugin_ping($event)"
    :keep_active_sync="keep_active"
    :popout_button="popout_button"
    :scroll_to.sync="scroll_to">

    <plugin-viewer-select
       :items="viewer_items"
       :selected.sync="viewer_selected"
       label="Viewer"
       :show_if_single_entry="false"
       hint="Select a viewer to search."
    />

    <plugin-file-import-select
      :items="catalog_items"
      :selected.sync="catalog_selected"
      label="Catalog"
      hint="Select a catalog to search."
      :from_file.sync="from_file"
      :from_file_message="from_file_message"
      dialog_title="Import Catalog"
      dialog_hint="Select a file containing a catalog"
      @click-cancel="file_import_cancel()"
      @click-import="file_import_accept()"
    >
      <g-file-import id="file-uploader"></g-file-import>
    </plugin-file-import-select>

    <v-row v-if="catalog_selected === 'Gaia'">
      <j-docs-link>
        See the <j-external-link link='https://astroquery.readthedocs.io/en/latest/gaia/gaia.html' linktext='astropy.gaia docs'></j-external-link> for details on the query defaults.
      </j-docs-link>
    </v-row>
    
    <v-row v-if="catalog_selected && catalog_selected.endsWith('.ecsv')">
      <v-select
        v-model="selected_columns"
        :items="column_names"
        label="Select Columns"
        multiple
        hint="Select columns to display in the table."
      />
    </v-row>

    <v-row>
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
      ></v-text-field>
    </v-row>

    <v-row class="row-no-outside-padding">
       <v-col>
         <plugin-action-button
            :results_isolated_to_plugin="true"
            @click="do_search"
            :spinner="spinner"
          >
            Search
          </plugin-action-button>
       </v-col>
       <v-col>
         <plugin-action-button
            :results_isolated_to_plugin="true"
            @click="zoom_in"
          >
            Zoom to Selected
          </plugin-action-button>
       </v-col>
    </v-row>

    <v-row>
       <p class="font-weight-bold">Results:</p>
       <span style='padding-left: 4px' v-if="results_available">{{number_of_results}}</span>
    </v-row>

    <jupyter-widget :widget="table_selected_widget"></jupyter-widget>

    <jupyter-widget :widget="table_widget"></jupyter-widget> 

  </j-tray-plugin>
</template>