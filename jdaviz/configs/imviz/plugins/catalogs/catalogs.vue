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
         :items="catalog_items"
         v-model="catalog_selected"
         label="Catalog"
         hint="Select a catalog to search with."
         persistent-hint
       ></v-select>
     </v-row>

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
