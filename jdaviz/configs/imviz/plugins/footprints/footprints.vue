<template>
  <j-tray-plugin
    description='Show instrument footprints as overlays on image viewers.'
    :link="docs_link || 'https://jdaviz.readthedocs.io/en/'+vdocs+'/'+config+'/plugins.html#footprints'"
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

    <div v-if="is_pixel_linked">
      <v-alert type='warning' style="margin-left: -12px; margin-right: -12px">
          cannot plot footprint when pixel-linked (see Links Control plugin)
          <v-row justify="center">
            <v-btn @click="link_by_wcs">
              link by WCS
            </v-btn>
          </v-row>
      </v-alert>
    </div>
    <div v-if="viewer_items.length===0">
      <v-alert type='warning' style="margin-left: -12px; margin-right: -12px">
          no valid viewers (with necessary WCS information) to show footprint overlay
      </v-alert>
    </div>
  
    <div v-if="!is_pixel_linked && viewer_items.length > 0 && overlay_selected.length > 0">
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
      <v-alert v-if="!has_pysiaf" type="warning" style="margin-left: -12px; margin-right: -12px">
        <span>To use JWST footprints, install pysiaf and restart jdaviz</span>
      </v-alert>

      <plugin-file-import-select
        :items="preset_items"
        :selected.sync="preset_selected"
        label="Preset"
        hint="Preset instrument or import from a file."
        :from_file.sync="from_file"
        :from_file_message="from_file_message"
        dialog_title="Import Region"
        dialog_hint="Select a region file"
        @click-cancel="file_import_cancel()"
        @click-import="file_import_accept()"
      >
        <g-file-import id="file-uploader"></g-file-import>
      </plugin-file-import-select>

      <div v-if="preset_selected !== 'From File...' && preset_selected !== 'None'">
        <v-row>
          <span style="line-height: 36px; font-size: 12px; color: #666666; width: 100%">Center RA/Dec</span>
          <j-tooltip v-for="viewer_ref in viewer_selected" :tooltipcontent="'center RA/DEC on current zoom-limits of '+viewer_ref">
          <v-btn @click="() => center_on_viewer(viewer_ref)">
            {{viewer_ref}}
          </v-btn>
          </j-tooltip>
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
