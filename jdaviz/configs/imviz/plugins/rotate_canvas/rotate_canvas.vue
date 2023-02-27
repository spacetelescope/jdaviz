<template>
  <j-tray-plugin>
    <v-row>
      <j-docs-link :link="'https://jdaviz.readthedocs.io/en/'+vdocs+'/'+config+'/plugins.html#canvas-rotation'">Rotate viewer canvas to any orientation (note: this does not affect the underlying data).</j-docs-link>
    </v-row>

    <plugin-viewer-select
      :items="viewer_items"
      :selected.sync="viewer_selected"
      label="Viewer"
      hint="Select viewer."
    />
    
    <v-row>
      <v-slider
        v-model="angle"
        class="align-center"
        max="180"
        min="-180"
        step="1"
        color="#00617E"
        track-color="#00617E"
        thumb-color="#153A4B"
        hide-details
      >
      </v-slider>
    </v-row>

    <v-row>
      <v-col>
        <v-text-field
          v-model.number="angle"
          type="number"
          label="Angle"
          hint="Rotation angle in degrees clockwise"
        ></v-text-field>
      </v-col>
    </v-row>

    

  </j-tray-plugin>
</template>
