<template>
  <j-tray-plugin>
    <v-row>
      <j-docs-link :link="'https://jdaviz.readthedocs.io/en/'+vdocs+'/'+config+'/plugins.html#plot-options'">Viewer and data/layer options.</j-docs-link>
    </v-row>
  
    <v-row justify="end">
      <v-btn
        icon
        @click="() => {multiselect = !multiselect}"
      >
        <v-icon>{{multiselect ? 'mdi-checkbox-multiple-marked-outline' : 'mdi-checkbox-marked-outline'}}</v-icon>
      </v-btn>
    </v-row>

    <plugin-viewer-select
      :items="viewer_items"
      :selected.sync="viewer_selected"
      :multiselect="multiselect"
      :label="multiselect ? 'Viewers' : 'Viewer'"
      :hint="multiselect ? 'Select viewers to set options simultaneously' : 'Select the viewer to set options.'"
    />

    <div>
      <plugin-layer-select
        :items="layer_items"
        :selected.sync="layer_selected"
        :multiselect="multiselect"
        :label="multiselect ? 'Layers': 'Layer'"
        :hint="multiselect ? 'Select layers to set options simultaneously' : 'Select the data or subset to set options.'"
      />
    </div>

  </j-tray-plugin>
</template>
