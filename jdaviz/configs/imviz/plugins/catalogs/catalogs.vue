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

     <v-dialog :value="catalog_selected === 'From File...' && from_file.length === 0" height="400" width="600">
       <v-card>
         <v-card-title class="headline" color="primary" primary-title>Load Catalog</v-card-title>
         <v-card-text>
           Select a file containing a catalog.
           <v-container>
             <v-row>
               <v-col>
                 <g-file-import id="file-uploader"></g-file-import>
               </v-col>
             </v-row>
             <v-row v-if="from_file_message.length > 0" :style='"color: red"'>
               {{from_file_message}}
             </v-row>
             <v-row v-else>
               Valid catalog file
             </v-row>
           </v-container>
         </v-card-text>

         <v-card-actions>
           <div class="flex-grow-1"></div>
           <v-btn color="primary" text @click="catalog_selected = catalog_items[0].label">Cancel</v-btn>
           <v-btn color="primary" text @click="set_file_from_dialog" :disabled="from_file_message.length > 0">Load</v-btn>
         </v-card-actions>

       </v-card>
    </v-dialog>

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
