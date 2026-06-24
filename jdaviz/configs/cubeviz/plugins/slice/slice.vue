<template>
  <j-tray-plugin
      :config="config"
      :plugin_key="plugin_key || 'Slice'"
      v-model:api_hints_enabled="api_hints_enabled"
      :description="docs_description"
      :irrelevant_msg="irrelevant_msg"
      :link="docs_link || 'https://jdaviz.readthedocs.io/en/'+vdocs+'/'+config+'/plugins.html#slice'"
      :popout_button="popout_button"
      v-model:scroll_to="scroll_to">

    <j-flex-row>
      <v-expansion-panels popout>
        <v-expansion-panel>
          <v-expansion-panel-title v-slot="{ open }">
            <span style="padding: 6px">Indicator Settings</span>
          </v-expansion-panel-title>
          <v-expansion-panel-text class="plugin-expansion-panel-content">
            <j-flex-row v-if="allow_disable_snapping">
              <plugin-switch
                  v-model:value="snap_to_slice"
                  label="Snap to Slice"
                  api_hint="plg.snap_to_slice = "
                  :api_hints_enabled="api_hints_enabled"
                  hint="Snap indicator (and value) to the nearest slice in the cube."
              />
            </j-flex-row>
            <j-flex-row>
              <plugin-switch
                  v-model:value="show_indicator"
                  label="Show Indicator"
                  api_hint="plg.show_indicator = "
                  :api_hints_enabled="api_hints_enabled"
                  hint="Show slice indicator even when slice tool is inactive."
              />
            </j-flex-row>
            <j-flex-row>
              <plugin-switch
                  v-model:value="show_value"
                  label="Show Value"
                  api_hint="plg.show_value = "
                  :api_hints_enabled="api_hints_enabled"
                  :hint="'Show slice '+value_label.toLowerCase()+' in label to right of indicator.'"
              />
            </j-flex-row>
          </v-expansion-panel-text>
        </v-expansion-panel>
      </v-expansion-panels>
    </j-flex-row>

    <j-flex-row justify="end" class="ignore-api-hints">
      <v-btn color="primary" variant="text" v-if="!cube_viewer_exists" @click="create_cube_viewer">
        Show Cube Viewer
      </v-btn>
    </j-flex-row>

    <j-flex-row>
      <v-text-field
          type="number"
          v-model.number="value"
          @focus="(e) => value_editing = true"
          @blur="(e) => value_editing = false"
          :label="api_hints_enabled ? 'plg.value =' : value_label"
          :class="api_hints_enabled ? 'api-hint' : null"
          :hint="value_label+' corresponding to slice.'+(snap_to_slice && value_editing ? '  Indicator will snap to slice when clicking or tabbing away from input.' : '')"
          :suffix="value_unit"
      ></v-text-field>
    </j-flex-row>

    <v-row class="row-no-outside-padding row-min-bottom-padding ignore-api-hints vuetify2">
      <v-col>
        <v-tooltip location="top">
          <template v-slot:activator="{ props }">
            <v-btn variant="text" icon @click="goto_first" v-bind="props" :disabled="is_playing">
              <v-icon>mdi-skip-previous</v-icon>
            </v-btn>
          </template>
          <span>Jump to first</span>
        </v-tooltip>
        <v-tooltip location="top">
          <template v-slot:activator="{ props }">
            <v-btn variant="text" icon @click="play_prev" v-bind="props" :disabled="is_playing">
              <span class="slice-step-button-label">-1</span>
            </v-btn>
          </template>
          <span>Previous</span>
        </v-tooltip>
        <v-tooltip location="top">
          <template v-slot:activator="{ props }">
            <v-btn variant="text" icon @click="play_start_stop" v-bind="props">
              <v-icon>mdi-play-pause</v-icon>
            </v-btn>
          </template>
          <span>Play/Pause</span>
        </v-tooltip>
        <v-tooltip location="top">
          <template v-slot:activator="{ props }">
            <v-btn variant="text" icon @click="play_next" v-bind="props" :disabled="is_playing">
              <span class="slice-step-button-label">+1</span>
            </v-btn>
          </template>
          <span>Next</span>
        </v-tooltip>
        <v-tooltip location="top">
          <template v-slot:activator="{ props }">
            <v-btn variant="text" icon @click="goto_last" v-bind="props" :disabled="is_playing">
              <v-icon>mdi-skip-next</v-icon>
            </v-btn>
          </template>
          <span>Jump to last</span>
        </v-tooltip>
      </v-col>
    </v-row>
  </j-tray-plugin>
</template>

<script>
  export default {
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

.slice-step-button-label {
  font-weight: 600;
}
</style>
