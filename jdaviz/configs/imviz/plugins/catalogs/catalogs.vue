<template>
  <j-tray-plugin
     description='Queries an area encompassed by the viewer using a specified catalog and marks all the objects found within the area.'
    :link="docs_link || 'https://jdaviz.readthedocs.io/en/'+vdocs+'/'+config+'/plugins.html#catalog-search'"
    :popout_button="popout_button">

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

    <v-row class="row-no-outside-padding">
       <v-col>
         <plugin-action-button
            :results_isolated_to_plugin="true"
            @click="do_clear"
          >
            Clear
          </plugin-action-button>
       </v-col>
       <v-col>
         <plugin-action-button
            :results_isolated_to_plugin="true"
            @click="do_search"
            :spinner="spinner"
          >
            Search
          </plugin-action-button>
       </v-col>
    </v-row>

    <v-row>
       <p class="font-weight-bold">Results:</p>
       <span style='padding-left: 4px' v-if="results_available">{{number_of_results}}</span>
    <v-row>

  </j-tray-plugin>
</template>
