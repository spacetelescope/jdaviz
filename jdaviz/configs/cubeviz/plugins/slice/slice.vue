<template>
  <j-tray-plugin>
    <v-row>
      <j-docs-link :link="'https://jdaviz.readthedocs.io/en/'+vdocs+'/'+config+'/plugins.html#slice'">Select slice (or wavelength) of the cube to show in the image viewers and highlighted in the spectrum viewer.  The slice can also be changed interactively in the spectrum viewer by activating the slice tool.</j-docs-link>
    </v-row>
    
    <v-row>
      <v-slider
        :value="slider"
        @input="throttledSetValue"
        class="align-center"
        :max="max_value"
        :min="min_value"
        hide-details
      />
    </v-row>

    <v-row>
      <v-text-field
        v-model="slider"
        class="mt-0 pt-0"
        type="number"
        label="Slice"
        hint="Slice number"
      ></v-text-field>
    </v-row>

    <v-row>
      <v-text-field
        v-model="wavelength"
        class="mt-0 pt-0"
        @change="change_wavelength"
        label="Wavelength"
        hint="Wavelength corresponding to slice, in units of spectrum"
      ></v-text-field>
    </v-row>
  </j-tray-plugin>
</template>

<script>
  module.exports = {
    created() {
      this.throttledSetValue = _.throttle(
        (v) => { this.slider = v; },
        this.wait);
    },
  }
</script>

<style lang="sass">
  $slider-transition: none !important
</style>
