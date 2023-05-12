<template>
  <j-tray-plugin  
    description="Rotate viewer canvas to any orientation (note: this does not affect the underlying data)."
    :link="'https://jdaviz.readthedocs.io/en/'+vdocs+'/'+config+'/plugins.html#canvas-rotation'"
    :disabled_msg="isChromium() ? '' : 'Image rotation is not supported by your browser. Please see our docs for more information.'"
    :popout_button="popout_button">
    <plugin-viewer-select
      :items="viewer_items"
      :selected.sync="viewer_selected"
      label="Viewer"
      hint="Select viewer."
    />

    <v-row>
      <span style="line-height: 36px">Presets:</span>
      <j-tooltip tooltipcontent="reset rotation and flip">
        <v-btn icon @click="reset">
          <v-icon>mdi-restore</v-icon>
        </v-btn>
      </j-tooltip>
      <j-tooltip v-if="has_wcs" tooltipcontent="north up, east right">
        <v-btn icon @click="set_north_up_east_right">
          <img :src="icon_nuer" width="24" class="invert-if-dark" style="opacity: 0.65"/>
        </v-btn>
      </j-tooltip>
      <j-tooltip v-if="has_wcs" tooltipcontent="north up, east left">
        <v-btn icon @click="set_north_up_east_left">
          <img :src="icon_nuel" width="24" class="invert-if-dark" style="opacity: 0.65"/>
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
      <v-switch v-model="flip_horizontal" label="Flip horizontally after rotation"></v-switch>
    </v-row>

  </j-tray-plugin>
</template>

<script>
module.exports = {
  methods: {
    isChromium() {
      try {
        for (brand_version_pair of navigator.userAgentData.brands) {
            if (brand_version_pair.brand == "Chromium"){
                return true;
            }
        }
        return false;
      }
      catch {
        return false
      }
    }
  }
}
</script>