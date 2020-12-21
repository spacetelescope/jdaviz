<template>
  <!-- <v-toolbar-items> -->
  <!-- <v-divider vertical></v-divider> -->
  <div>
    <v-slider
      :value="slider"
      @input="throttledSetValue"
      class="align-center"
      :max="max_value"
      :min="min_value"
      hide-details
      style="max-width: 33%; min-width: 300px"
      :step="slider_step"
    >
    <template v-slot:prepend>
      <v-divider vertical></v-divider>
      <v-select
        class="pl-md-4"
        :items="['Redshift', 'RV (km/s)']"
        v-model="slider_type"
        dense>
      </v-select>
    </template>
    <template v-slot:append>
        <v-text-field
          v-model="slider_textbox"
          class="mt-0 pt-0"
          hide-details
          single-line
          filled
          dense
      ></v-text-field>
    </template>
    </v-slider>
  </div>
  <!-- </v-toolbar-items> -->
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
