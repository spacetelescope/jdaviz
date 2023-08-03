<template>
  <j-tray-plugin
    description='Show instrument footprints as overlays on image viewers.'
    :link="'https://jdaviz.readthedocs.io/en/'+vdocs+'/'+config+'/plugins.html#footprints'"
    :uses_active_status="uses_active_status"
    @plugin-ping="plugin_ping($event)"
    :keep_active.sync="keep_active"
    :popout_button="popout_button">

    <plugin-editable-select
      :mode.sync="footprint_mode"
      :edit_value.sync="footprint_edit_value"
      :items="footprint_items"
      :selected.sync="footprint_selected"
      label="Footprint"
      hint="Select a footprint to modify."
      >
    </plugin-editable-select>

    <div v-if="footprint_selected">
      <j-plugin-section-header>Overlay Options</j-plugin-section-header>

      <plugin-viewer-select
        :items="viewer_items"
        :selected.sync="viewer_selected"
        :multiselect="true"
        label="Viewers"
        :show_if_single_entry="false"
        hint="Select viewers to display this footprint"
      />

      <v-row>
        <span>
          <v-btn icon @click.stop="visible = !visible">
            <v-icon>mdi-eye{{ visible ? '' : '-off' }}</v-icon>
          </v-btn>
          Show Footprint Overlay
        </span>
      </v-row>

      <v-row>
          <v-menu>
            <template v-slot:activator="{ on }">
                <span class="linelist-color-menu"
                      :style="`background:${color}; cursor: pointer`"
                      @click.stop="on.click"
                >&nbsp;</span>
            </template>
            <div @click.stop="" style="text-align: end; background-color: white">
                <v-color-picker :value="color"
                            @update:color="throttledSetColor($event.hexa)"></v-color-picker>
            </div>
          </v-menu>
        <span>
          Footprint Overlay Color
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
          :items="instrument_items.map(i => i.label)"
          v-model="instrument_selected"
          label="Instrument"
          hint="Select instrument to define footprint."
          persistent-hint
        ></v-select>
      </v-row>

      <v-row v-if="pos_instruments.includes(instrument_selected)">
        <v-text-field
          v-model.number="ra"
          type="number"
          step="0.01"
          :rules="[() => ra!=='' || 'This field is required']"
          label="RA"
          hint="Right Ascension"
          persistent-hint
        ></v-text-field>
      </v-row>

      <v-row v-if="pos_instruments.includes(instrument_selected)">
        <v-text-field
          v-model.number="dec"
          type="number"
          step="0.01"
          :rules="[() => dec!=='' || 'This field is required']"
          label="Dec"
          hint="Declination"
          persistent-hint
        ></v-text-field>
      </v-row>

      <v-row v-if="pos_instruments.includes(instrument_selected)">
        <v-text-field
          v-model.number="pa"
          type="number"
          :rules="[() => pa!=='' || 'This field is required']"
          label="Position Angle"
          hint="Position Angle in degrees measured from North
                to central vertical axis in North to East direction."
          persistent-hint
        ></v-text-field>
      </v-row>

      <v-row v-if="offset_instruments.includes(instrument_selected)">
        <v-text-field
          v-model.number="v2_offset"
          type="number"
          :rules="[() => v2_offset!=='' || 'This field is required']"
          label="V2 Offset"
          hint="V2 Offset"
          persistent-hint
        ></v-text-field>
      </v-row>
      
      <v-row v-if="offset_instruments.includes(instrument_selected)">
        <v-text-field
          v-model.number="v3_offset"
          type="number"
          :rules="[() => v3_offset!=='' || 'This field is required']"
          label="V3 Offset"
          hint="V3 Offset"
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
