<template>
  <v-toolbar-items>
    <v-tooltip bottom>
      <template v-slot:activator="{ on }">
        <v-btn disabled v-on="on" icon tile>
          <v-icon>mdi-format-superscript</v-icon>
        </v-btn>
      </template>
      <span>Arithmetic Editor</span>
    </v-tooltip>
    <v-tooltip bottom>
      <template v-slot:activator="{ on }">
        <v-btn disabled v-on="on" icon tile>
          <v-icon>mdi-export</v-icon>
        </v-btn>
      </template>
      <span>Export Data</span>
    </v-tooltip>
    <v-tooltip bottom>
      <template v-slot:activator="{ on }">
        <v-btn disabled v-on="on" icon tile>
          <v-icon>mdi-delete</v-icon>
        </v-btn>
      </template>
      <span>Delete Data</span>
    </v-tooltip>
    <!-- <v-divider vertical></v-divider> -->
  </v-toolbar-items>
</template>
