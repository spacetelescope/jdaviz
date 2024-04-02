<template>
  <j-tray-plugin
    :description="docs_description || 'Select slice of the cube to show in the image viewers.  The slice can also be changed interactively in the spectrum viewer by activating the slice tool.'"
    :irrelevant_msg="irrelevant_msg"
    :link="docs_link || 'https://jdaviz.readthedocs.io/en/'+vdocs+'/'+config+'/plugins.html#slice'"
    :popout_button="popout_button"
    :scroll_to.sync="scroll_to">

    <v-row>
      <v-expansion-panels popout>
        <v-expansion-panel>
          <v-expansion-panel-header v-slot="{ open }">
            <span style="padding: 6px">Indicator Settings</span>
          </v-expansion-panel-header>
          <v-expansion-panel-content class="plugin-expansion-panel-content">
            <v-row v-if="allow_disable_snapping">
              <v-switch
                label="Snap to Slice"
                hint="Snap indicator (and value) to the nearest slice in the cube."
                v-model="snap_to_slice"
                persistent-hint>
              </v-switch>
            </v-row>
            <v-row>
              <v-switch
                label="Show Indicator"
                hint="Show slice indicator even when slice tool is inactive."
                v-model="show_indicator"
                persistent-hint>
              </v-switch>
            </v-row>
            <v-row>
              <v-switch
                label="Show Value"
                :hint="'Show slice '+value_label.toLowerCase()+' in label to right of indicator.'"
                v-model="show_value"
                persistent-hint>
              </v-switch>
            </v-row>
          </v-expansion-panel-content>
        </v-expansion-panel>
      </v-expansion-panels>
    </v-row>

    <v-row justify="end">
      <v-btn color="primary" text v-if="!cube_viewer_exists" @click="create_cube_viewer">
        Show Cube Viewer
      </v-btn>
    </v-row>

    <v-row>
      <v-text-field
        type="number"
        v-model.number="value"
        @focus="(e) => value_editing = true"
        @blur="(e) => value_editing = false"
        class="mt-0 pt-0"
        :label="value_label"
        :hint="value_label+' corresponding to slice.'+(snap_to_slice && value_editing ? '  Indicator will snap to slice when clicking or tabbing away from input.' : '')"
        :suffix="value_unit"
      ></v-text-field>
    </v-row>

    <v-row class="row-no-outside-padding row-min-bottom-padding">
      <v-col>
        <v-tooltip top>
          <template v-slot:activator="{ on, attrs }">
            <v-btn color="primary" icon @click="goto_first" v-bind="attrs" v-on="on" :disabled="is_playing">
              <v-icon>skip_previous</v-icon>
            </v-btn>
          </template>
          <span>Jump to first</span>
        </v-tooltip>
        <v-tooltip top>
          <template v-slot:activator="{ on, attrs }">
            <v-btn color="primary" icon @click="play_prev" v-bind="attrs" v-on="on" :disabled="is_playing">
              <v-icon>exposure_minus_1</v-icon>
            </v-btn>
          </template>
          <span>Previous</span>
        </v-tooltip>
        <v-tooltip top>
          <template v-slot:activator="{ on, attrs }">
            <v-btn color="primary" icon @click="play_start_stop" v-bind="attrs" v-on="on">
              <v-icon>mdi-play-pause</v-icon>
            </v-btn>
          </template>
          <span>Play/Pause</span>
        </v-tooltip>
        <v-tooltip top>
          <template v-slot:activator="{ on, attrs }">
            <v-btn color="primary" icon @click="play_next" v-bind="attrs" v-on="on" :disabled="is_playing">
              <v-icon>exposure_plus_1</v-icon>
            </v-btn>
          </template>
          <span>Next</span>
        </v-tooltip>
        <v-tooltip top>
          <template v-slot:activator="{ on, attrs }">
            <v-btn color="primary" icon @click="goto_last" v-bind="attrs" v-on="on" :disabled="is_playing">
              <v-icon>skip_next</v-icon>
            </v-btn>
          </template>
          <span>Jump to last</span>
        </v-tooltip>
      </v-col>
    </v-row>
  </j-tray-plugin>
</template>

<script>
  module.exports = {
    created() {
      this.throttledSetValue = _.throttle(
        (v) => { this.slice = v; },
        this.slider_throttle);
    },
  }
</script>

<style>
  .v-slider {
    margin: 0px !important;
  }
</style>
