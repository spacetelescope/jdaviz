<template>
   <j-tray-plugin
     description='Queries an area encompassed by the viewer using the SDSS and marks all the objects found within the area in the given catalog.'
    :link="'https://jdaviz.readthedocs.io/en/latest/dev/ui_plugin_components.html'"
    :popout_button="popout_button">

     <v-row>
       <v-select
         :items="viewer_items"
         v-model="selected_viewer"
         label="Viewer"
         hint="Select a viewer to search."
         persistent-hint
       ></v-select>
     </v-row>

     <v-row justify="end">
       <v-btn color="primary" text @click="do_catalogs">SDSS Search</v-btn>
     </v-row>

     <v-row justify="end">
       <v-btn color="primary" text @click="do_clear">Clear</v-btn>
     </v-row>

     <v-row v-if="results_available">
       <p class="font-weight-bold">Results:</p>
       <span style='padding-left: 4px'>{{number_of_results}}</span>
     <v-row>

   </j-tray-plugin>
 </template>
