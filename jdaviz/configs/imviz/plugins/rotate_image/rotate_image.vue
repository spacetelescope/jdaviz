<template>
  <j-tray-plugin>
    <v-row>
      <j-docs-link :link="'https://jdaviz.readthedocs.io/en/'+vdocs+'/'+config+'/plugins.html#simple-image-rotation'">Rotate image.</j-docs-link>
    </v-row>

    <plugin-viewer-select
      :items="viewer_items"
      :selected.sync="viewer_selected"
      label="Viewer"
      hint="Select viewer."
    />

    <v-row>
      <v-col>
        <v-text-field
          v-model="angle"
          type="number"
          label="Angle"
          hint="Rotation angle in degrees counter-clockwise"
        ></v-text-field>
      </v-col>
    </v-row>

    <v-row justify="end">
      <v-btn color="primary" text @click="rotate_image">Rotate</v-btn>
    </v-row>

  </j-tray-plugin>
</template>
