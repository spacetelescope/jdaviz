<template>
  <j-tray-plugin
    :config="config"
    plugin_key="Footprints"
    :api_hints_enabled.sync="api_hints_enabled"
    :description="docs_description"
    :link="docs_link || 'https://jdaviz.readthedocs.io/en/'+vdocs+'/'+config+'/plugins.html#footprints'"
    :uses_active_status="uses_active_status"
    @plugin-ping="plugin_ping($event)"
    :keep_active.sync="keep_active"
    :disabled_msg="disabled_msg"
    :popout_button="popout_button"
    :scroll_to.sync="scroll_to">

    <plugin-editable-select
      :mode.sync="overlay_mode"
      :edit_value.sync="overlay_edit_value"
      :items="overlay_items"
      :selected.sync="overlay_selected"
      label="Overlay"
      api_hint="plg.overlay ="
      api_hint_add="plg.add_overlay"
      api_hint_rename="plg.rename_overlay"
      api_hint_remove="plg.remove_overlay"
      :api_hints_enabled="api_hints_enabled"
      hint="Select an overlay to modify."
      >
    </plugin-editable-select>

    <v-alert
      v-if="is_pixel_linked"
      type='warning'
      style="margin-left: -12px; margin-right: -12px"
    >
      cannot plot footprint when aligned by pixels (see Orientation plugin).
      <v-row justify="end" style="margin-right: 2px; margin-top: 16px">
        <v-btn @click="link_by_wcs">
          link by WCS
        </v-btn>
      </v-row>
    </v-alert>
    <v-alert v-if="viewer_items.length===0" type='warning' style="margin-left: -12px; margin-right: -12px">
      no valid viewers (with necessary WCS information) to show footprint overlay.
    </v-alert>
  
    <div v-if="!is_pixel_linked && viewer_items.length > 0 && overlay_selected.length > 0">
      <j-plugin-section-header>Display Options</j-plugin-section-header>

      <plugin-viewer-select
        :items="viewer_items"
        :selected.sync="viewer_selected"
        :multiselect="true"
        label="Viewers"
        api_hint="plg.viewer ="
        :api_hints_enabled="api_hints_enabled"
        :show_if_single_entry="false"
        hint="Select viewers to display this overlay"
      />

      <v-row>
        <plugin-switch
          :value.sync="visible"
          label="Visible"
          api_hint="plg.visible = "
          :api_hints_enabled="api_hints_enabled"
          :use_eye_icon="true"
        />
      </v-row>

      <v-row>
        <plugin-color-picker
          label='Overlay Color'
          label_inline="true"
          api_hint="plg.color = "
          :api_hints_enabled="api_hints_enabled"
          :value="color"
          @color-update="throttledSetColor($event.hexa)"
        />
      </v-row>
      <v-row>
        <plugin-slider
          label="Fill Opacity"
          api_hint="plg.fill_opacity = "
          :api_hints_enabled="api_hints_enabled"
          :wait="300"
          max="1"
          step="0.01"
          :value.sync="fill_opacity"
        />
      </v-row>

      <j-plugin-section-header>Footprint Definition</j-plugin-section-header>
      <v-alert v-if="!has_pysiaf" type="warning" style="margin-left: -12px; margin-right: -12px">
        To use JWST or Roman footprints, install pysiaf and restart jdaviz. This can be done by going to the command line
        and running `pip install pysiaf` and then launching Jdaviz.
      </v-alert>

      <plugin-select-filter
        :items="preset_obs_items"
        :selected.sync="preset_obs_selected"
        @update:selected="($event) => {preset_obs_selected = $event}"
        tooltip_suffix="footprints in preset list"
        api_hint="plg.preset_obs ="
        :api_hints_enabled="api_hints_enabled"
      />

      <plugin-file-import-select
        :items="preset_items"
        :selected.sync="preset_selected"
        label="Preset"
        hint="Preset instrument or import from a file."
        api_hint="plg.preset ="
        :api_hints_enabled="api_hints_enabled"
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
          <v-btn
            @click="() => center_on_viewer(viewer_ref)"
            :class="api_hints_enabled ? 'api-hint' : null"
          >
            {{ api_hints_enabled ?
                'plg.center_on_viewer(\''+viewer_ref+'\')'
                :
                viewer_ref
            }}
          </v-btn>
          </j-tooltip>
        </v-row>

        <v-row>
          <v-text-field
            v-model.number="ra"
            type="number"
            step="0.01"
            :rules="[() => ra!=='' || 'This field is required']"
            :label="api_hints_enabled ? 'plg.ra = ' : 'RA'"
            :class="api_hints_enabled ? 'api-hint' : null"
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
            :label="api_hints_enabled ? 'plg.dec = ' : 'Dec'"
            :class="api_hints_enabled ? 'api-hint' : null"
            hint="Declination (degrees)"
            persistent-hint
          ></v-text-field>
        </v-row>

        <v-row>
          <v-text-field
            v-model.number="pa"
            type="number"
            :rules="[() => pa!=='' || 'This field is required']"
            :label="api_hints_enabled ? 'plg.pa = ' : 'Position Angle'"
            :class="api_hints_enabled ? 'api-hint' : null"
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
            :label="api_hints_enabled ? 'plg.v2_offset = ' : 'V2 Offset'"
            :class="api_hints_enabled ? 'api-hint' : null"
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
            :label="api_hints_enabled ? 'plg.v3_offset = ' : 'V3 Offset'"
            :class="api_hints_enabled ? 'api-hint' : null"
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
    },
    methods: {
      boolToString(b) {
        if (b) {
          return 'True'
        } else {
          return 'False'
        }
      },
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
