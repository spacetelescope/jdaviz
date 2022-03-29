<template>
  <j-tray-plugin>
    <v-row>
      <j-docs-link :link="'https://jdaviz.readthedocs.io/en/'+vdocs+'/'+config+'/plugins.html#export-plot'">Export viewer plot as an image.</j-docs-link>
    </v-row>

    <plugin-viewer-select
      :items="viewer_items"
      :selected.sync="viewer_selected"
      label="Viewer"
      hint="Select the viewer to export."
    />

    <div v-if="viewer_selected">
      <v-list>
       <v-list-item>
        <v-btn
         color="primary"
         @click="() => save_figure('png')"
        >
         Export to PNG
        </v-btn>
       </v-list-item>
       <v-list-item>
        <v-btn
         color="primary"
         @click="() => save_figure('svg')"
        >
         Export to SVG
        </v-btn>
       </v-list-item>
      </v-list>
    </div>

  </j-tray-plugin>
</template>
