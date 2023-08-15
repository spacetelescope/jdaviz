<template>
  <j-tray-plugin
     description='Queries an area encompassed by the viewer using a specified catalog and marks all the objects found within the area.'
    :link="'https://jdaviz.readthedocs.io/en/'+vdocs+'/'+config+'/plugins.html#catalog-search'"
    :popout_button="popout_button">

    <plugin-viewer-select
       :items="viewer_items"
       :selected.sync="viewer_selected"
       label="Viewer"
       :show_if_single_entry="false"
       hint="Select a viewer to search."
    />

    <v-row>
       <v-select
         :menu-props="{ left: true }"
         attach
         :items="catalog_items.map(i => i.label)"
         v-model="catalog_selected"
         label="Catalog"
         hint="Select a catalog to search with."
         persistent-hint
       ></v-select>
       <v-chip v-if="catalog_selected === 'From File...'"
         close
         close-icon="mdi-close"
         label
         @click:close="() => {if (from_file.length) {from_file = ''} else {catalog_selected = catalog_items[0].label}}"
         style="margin-top: -50px; width: 100%"
       >
        <!-- @click:close resets from_file and relies on the @observe in python to reset catalog 
             to its default, but the traitlet change wouldn't be fired if from_file is already
             empty (which should only happen if setting from the API but not setting from_file) -->
          <span style="overflow-x: hidden; whitespace: nowrap; text-overflow: ellipsis; width: 100%">
            {{from_file.split("/").slice(-1)[0]}}
          </span>
       </v-chip>
    </v-row>

    <plugin-file-import
      title="Import Catalog"
      hint="Select a file containing a catalog"
      :show="catalog_selected === 'From File...' && from_file.length === 0"
      :from_file="from_file"
      :from_file_message.sync="from_file_message"
      @click-cancel="catalog_selected=catalog_items[0].label"
      @click-import="file_import_accept()">
        <g-file-import id="file-uploader"></g-file-import>
    </plugin-file-import>

    <v-row class="row-no-outside-padding">
       <v-col>
         <v-btn color="primary" text @click="do_clear">Clear</v-btn>
       </v-col>
       <v-col>
         <v-btn color="primary" text @click="do_search">Search</v-btn>
       </v-col>
    </v-row>

    <v-row>
       <p class="font-weight-bold">Results:</p>
       <span style='padding-left: 4px' v-if="results_available">{{number_of_results}}</span>
    <v-row>

  </j-tray-plugin>
</template>
 
<style scoped>
  .v-chip__content {
    width: 100%
  }
</style>
