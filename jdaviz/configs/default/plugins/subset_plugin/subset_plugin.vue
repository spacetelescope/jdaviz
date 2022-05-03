<template>
  <j-tray-plugin>
    <v-row>
      <j-docs-link :link="'https://jdaviz.readthedocs.io/en/'+vdocs+
                          '/specviz/displaying.html#defining-spectral-regions'">
        Tools for selecting and interacting with subsets.
      </j-docs-link>
    </v-row>
    
    <plugin-subset-select 
      :items="subset_items"
      :selected.sync="subset_selected"
      :show_if_single_entry="true"
      label="Subset"
      hint="Select subset to edit."
    />

    <v-row>
      <g-subset-mode></g-subset-mode>
    </v-row>

    <div v-if="show_region_info">
      <j-plugin-section-header>Subset Region Definition</j-plugin-section-header>
      <v-row><v-row>
    </div>
  </j-tray-plugin>
</template>
