<template>
  <j-tray-plugin>
    <v-row>
      <j-docs-link :link="'https://jdaviz.readthedocs.io/en/'+vdocs+'/'+config+'/plugins.html#compass'">
        Show active data label, compass, and zoom box.
      </j-docs-link>
    </v-row>

    <v-row>
      <v-select
        :items="viewer_items"
        v-model="selected_viewer"
        label="Viewer"
        hint="Select a viewer to show."
        persistent-hint
      ></v-select>
    </v-row>

    <v-row v-if="data_label">
      <v-chip
        label=true
      >{{ data_label }}</v-chip>
    </v-row>

    <img v-if="img_data" :src="`data:image/png;base64,${img_data}`" style="width: 100%; max-width: 400px" />

  </j-tray-plugin>
</template>
