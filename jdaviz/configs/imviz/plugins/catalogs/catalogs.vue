<template>
   <j-tray-plugin>
     <v-row>
       Catalogs queries an area encompassed by a given radius centered on a given RA and Dec and returns all the objects found within the area in the given catalog.
     </v-row>

     <v-row justify="end">
       <v-btn color="primary" text @click="do_catalogs">Query Search</v-btn>
     </v-row>

   </j-tray-plugin>
 </template>