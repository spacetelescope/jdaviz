<template>
  <j-tray-plugin
    :description="docs_description || 'Select slice of the cube to show in the image viewers.  The slice can also be changed interactively in the spectrum viewer by activating the slice tool.'"
    :link="docs_link || 'https://jdaviz.readthedocs.io/en/'+vdocs+'/'+config+'/plugins.html#slice'"
    :popout_button="popout_button">

    <v-row>
      <v-expansion-panels popout>
        <v-expansion-panel>
          <v-expansion-panel-header v-slot="{ open }">
            <span style="padding: 6px">Indicator Settings</span>
          </v-expansion-panel-header>
          <v-expansion-panel-content class="plugin-expansion-panel-content">
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
                hint="Show slice value in label to right of indicator."
                v-model="show_value"
                persistent-hint>
              </v-switch>
            </v-row>
          </v-expansion-panel-content>
        </v-expansion-panel>
      </v-expansion-panels>
    </v-row>

    <v-row>
      <v-slider
        :value="slice"
        @input="throttledSetValue"
        class="align-center"
        :max="max_slice"
        :min="min_slice"
        hide-details
      />
    </v-row>

    <v-row>
      <v-text-field
        v-model.number="slice"
        class="mt-0 pt-0"
        type="number"
        label="Slice"
        hint="Slice number"
        :suffix="'/'+max_slice"
      ></v-text-field>
    </v-row>

    <v-row>
      <v-text-field
        v-model="value"
        class="mt-0 pt-0"
        :label="value_label"
        :hint="value_label+' corresponding to slice'"
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
          <span>Next slice</span>
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
        this.wait);
    },
  }
</script>

<style>
  .v-slider {
    margin: 0px !important;
  }
</style>
