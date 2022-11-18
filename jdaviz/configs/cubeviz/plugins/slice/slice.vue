<template>
  <j-tray-plugin
    description='Select slice (or wavelength) of the cube to show in the image viewers and highlighted in the spectrum viewer.  The slice can also be changed interactively in the spectrum viewer by activating the slice tool.'
    :link="'https://jdaviz.readthedocs.io/en/'+vdocs+'/'+config+'/plugins.html#slice'"
    :popout_button="popout_button">

    <v-row>
      <v-expansion-panels popout>
        <v-expansion-panel>
          <v-expansion-panel-header v-slot="{ open }">
            <span style="padding: 6px">Indicator Settings</span>
          </v-expansion-panel-header>
          <v-expansion-panel-content>
            <v-row>
              <v-switch
                label="Show Indicator"
                hint="Show indicator in spectral viewer even when slice tool is inactive."
                v-model="show_indicator"
                persistent-hint>
              </v-switch>
            </v-row>
            <v-row>
              <v-switch
                label="Show Wavelength"
                hint="Show slice wavelength in label to right of indicator."
                v-model="show_wavelength"
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
        :max="max_value"
        :min="min_value"
        hide-details
      />
    </v-row>

    <v-row class="row-no-outside-padding row-min-bottom-padding">
      <v-col>
        <v-text-field
          v-model="slice"
          class="mt-0 pt-0"
          type="number"
          label="Slice"
          hint="Slice number"
        ></v-text-field>
      </v-col>
      <v-col cols=3>
        <span> / {{ max_value }}</span>
      </v-col>
    </v-row>

    <v-row class="row-no-outside-padding">
      <v-col>
        <v-text-field
          v-model="wavelength"
          class="mt-0 pt-0"
          label="Wavelength"
          hint="Wavelength corresponding to slice, in units of spectrum"
        ></v-text-field>
      </v-col>
      <v-col cols=3>
        <span>{{ wavelength_unit }}</span>
      </v-col>
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
