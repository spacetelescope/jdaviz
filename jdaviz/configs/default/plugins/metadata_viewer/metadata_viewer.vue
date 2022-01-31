<template>
  <j-tray-plugin>
    <v-row>
      <j-docs-link :link="'https://jdaviz.readthedocs.io/en/'+vdocs+'/'+config+'/plugins.html#metadata-viewer'">View metadata.</j-docs-link>
    </v-row>

    <v-row>
      <v-select
        :items="dc_items"
        v-model="selected_data"
        label="Data"
        hint="Select the data to see metadata."
        persistent-hint
      ></v-select>
    </v-row>

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
