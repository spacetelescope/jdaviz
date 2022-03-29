<template>
  <j-tray-plugin>
    <v-row>
      <j-docs-link :link="'https://jdaviz.readthedocs.io/en/'+vdocs+'/'+config+'/plugins.html#metadata-viewer'">View metadata.</j-docs-link>
    </v-row>

    <!-- for specviz, we'll allow this to hide for a single entry, but since filters are being
         applied on other configs, we'll always show -->
    <plugin-dataset-select
      :items="dataset_items"
      :selected.sync="dataset_selected"
      :show_if_single_entry="config!='specviz'"
      label="Data"
      hint="Select the data to see metadata."
    />

    <div v-if="has_metadata">
      <j-plugin-section-header>Metadata</j-plugin-section-header>
      <v-row no-gutters>
        <v-col cols=6><U>Key</U></v-col>
        <v-col cols=6><U>Value</U></v-col>
      </v-row>
      <v-row
        v-for="item in metadata"
        :key="item[0]"
        no-gutters>
        <v-col cols=6>{{ item[0] }}</v-col>
        <v-col cols=6>{{ item[1] }}</v-col>
      </v-row>
    </div>

  </j-tray-plugin>
</template>
