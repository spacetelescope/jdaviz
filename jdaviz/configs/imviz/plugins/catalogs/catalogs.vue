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
         @click:close="() => from_file = ''"
         style="margin-top: -50px; width: 100%"
       >
          <span style="overflow-x: hidden; whitespace: nowrap; text-overflow: ellipsis; width: 100%">
            {{from_file.split("/").slice(-1)[0]}}
          </span>
       </v-chip>

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
 
 <style scoped>
 .v-chip__content {
   width: 100%
 }
 </style>
