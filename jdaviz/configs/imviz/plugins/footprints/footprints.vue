<template>
  <j-tray-plugin
    description='Show instrument footprints as overlays on image viewers.'
    :link="'https://jdaviz.readthedocs.io/en/'+vdocs+'/'+config+'/plugins.html#footprints'"
    :uses_active_status="uses_active_status"
    @plugin-ping="plugin_ping($event)"
    :keep_active.sync="keep_active"
    :disabled_msg="disabled_msg"
    :popout_button="popout_button">

    <plugin-editable-select
      :mode.sync="overlay_mode"
      :edit_value.sync="overlay_edit_value"
      :items="overlay_items"
      :selected.sync="overlay_selected"
      label="Overlay"
      hint="Select an overlay to modify."
      >
    </plugin-editable-select>

    <div v-if="overlay_selected">
      <j-plugin-section-header>Display Options</j-plugin-section-header>

      <plugin-viewer-select
        :items="viewer_items"
        :selected.sync="viewer_selected"
        :multiselect="true"
        label="Viewers"
        :show_if_single_entry="false"
        hint="Select viewers to display this overlay"
      />

      <v-row>
        <span>
          <v-btn icon @click.stop="visible = !visible">
            <v-icon>mdi-eye{{ visible ? '' : '-off' }}</v-icon>
          </v-btn>
          Show Overlay
        </span>
      </v-row>

      <v-row>
          <v-menu>
            <template v-slot:activator="{ on }">
                <span class="color-menu"
                      :style="`background:${color}; cursor: pointer; margin-left: 6px`"
                      @click.stop="on.click"
                >&nbsp;</span>
            </template>
            <div @click.stop="" style="text-align: end; background-color: white">
                <v-color-picker :value="color"
                            @update:color="throttledSetColor($event.hexa)"></v-color-picker>
            </div>
          </v-menu>
        <span style="padding-left: 12px; padding-top: 3px">
          Overlay Color
        </span>
      </v-row>
      <div>
        <v-subheader class="pl-0 slider-label" style="height: 12px">Fill Opacity</v-subheader>
        <glue-throttled-slider wait="300" max="1" step="0.01" :value.sync="fill_opacity" hide-details class="no-hint" />
      </div>

      <j-plugin-section-header>Footprint Definition</j-plugin-section-header>
      <v-row>
        <v-select
          :menu-props="{ left: true }"
          attach
          :items="preset_items.map(i => i.label)"
          v-model="preset_selected"
          label="Preset"
          hint="Select the preset instrument footprint."
          persistent-hint
        ></v-select>
      </v-row>

      <v-row>
        <v-text-field
          v-model.number="ra"
          type="number"
          step="0.01"
          :rules="[() => ra!=='' || 'This field is required']"
          label="RA"
          hint="Right Ascension (degrees)"
          persistent-hint
        ></v-text-field>
      </v-row>

      <v-row>
        <v-text-field
          v-model.number="dec"
          type="number"
          step="0.01"
          :rules="[() => dec!=='' || 'This field is required']"
          label="Dec"
          hint="Declination (degrees)"
          persistent-hint
        ></v-text-field>
      </v-row>

      <v-row>
        <v-text-field
          v-model.number="pa"
          type="number"
          :rules="[() => pa!=='' || 'This field is required']"
          label="Position Angle"
          hint="Position Angle (degrees) measured from North
                to central vertical axis in North to East direction."
          persistent-hint
        ></v-text-field>
      </v-row>

      <v-row>
        <v-text-field
          v-model.number="v2_offset"
          type="number"
          :rules="[() => v2_offset!=='' || 'This field is required']"
          label="V2 Offset"
          hint="Additional V2 offset in telescope coordinates to apply to instrument
                center, as from a dither pattern."
          persistent-hint
        ></v-text-field>
      </v-row>
      
      <v-row>
        <v-text-field
          v-model.number="v3_offset"
          type="number"
          :rules="[() => v3_offset!=='' || 'This field is required']"
          label="V3 Offset"
          hint="Additional V3 offset in telescope coordinates to apply to instrument
                center, as from a dither pattern."
          persistent-hint
        ></v-text-field>
      </v-row>
    </div>

  </j-tray-plugin>
</template>

<script>
  module.exports = {
    created() {
      this.throttledSetColor = _.throttle(
        (v) => { this.color = v },
        100);
    }
  }
</script>

<style>
  .v-slider {
    margin: 0px !important;
  }

  .color-menu {
      font-size: 16px;
      padding-left: 16px;
      border: 2px solid rgba(0,0,0,0.54);
  }
</style>
