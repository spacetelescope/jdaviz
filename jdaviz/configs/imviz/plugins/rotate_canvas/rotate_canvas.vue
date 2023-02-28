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
      <span style="line-height: 36px">Presets:</span>
      <j-tooltip tooltipcontent="north up, east right">
        <v-btn icon @click="set_north_up_east_right">
          <v-icon>mdi-angle-right</v-icon>
        </v-btn>
      </j-tooltip>
      <j-tooltip tooltipcontent="north up, east left">
        <v-btn icon @click="set_north_up_east_left">
          <v-icon style="transform: rotateY(180deg)">mdi-angle-right</v-icon>
        </v-btn>
      </j-tooltip>
    </v-row>
    
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

    <v-row>
      <v-switch v-model="flip" label="Flip horizontally after rotation"></v-switch>
    </v-row>

    

  </j-tray-plugin>
</template>
