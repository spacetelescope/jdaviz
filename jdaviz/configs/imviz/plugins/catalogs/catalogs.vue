<template>
  <j-tray-plugin
    :description="docs_description || 'Queries an area encompassed by the viewer using a specified catalog and marks all the objects found within the area.'"
    :link="docs_link || 'https://jdaviz.readthedocs.io/en/'+vdocs+'/'+config+'/plugins.html#catalog-search'"
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
       <span style='padding-left: 4px' v-if="results_available">{{ number_of_results }}</span>
    </v-row>

    <!-- Display Catalog Results Table -->
    <v-row v-if="results_available">
       <p class="font-weight-bold">Catalog Results:</p>
       <table>
           <thead>
               <tr>
                   <!-- Define column headers based on the catalog results -->
                   <th v-for="(header, index) in catalogHeaders" :key="index">{{ header }}</th>
               </tr>
           </thead>
           <tbody>
               <!-- Use v-for to loop through catalog results and display each row -->
               <tr v-for="(result, index) in catalogResults" :key="index">
                   <!-- Display data from each result -->
                   <td v-for="(value, key) in result" :key="key">{{ value }}</td>
               </tr>
           </tbody>
       </table>
    </v-row>

  </j-tray-plugin>
</template>

<script>
export default {
  props: {
    docs_description: String,
    docs_link: String,
    popout_button: Boolean,
    scroll_to: String,
    viewer_items: Array,
    viewer_selected: String,
    catalog_items: Array,
    catalog_selected: String,
    from_file: Boolean,
    from_file_message: String,
    results_available: Boolean,
    number_of_results: Number,
    catalogResults: Array, // This prop should be passed from the parent component or state
    catalogHeaders: Array // This prop should contain the headers for the table
  },
  methods: {
    do_clear() {
      this.$emit('clear');
    },
    do_search() {
      this.$emit('search');
    },
    file_import_cancel() {
      this.$emit('file-import-cancel');
    },
    file_import_accept() {
      this.$emit('file-import-accept');
    }
  }
}
</script>
