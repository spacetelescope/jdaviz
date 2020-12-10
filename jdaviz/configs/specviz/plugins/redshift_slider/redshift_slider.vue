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
      label="Redshift"
    >
      <template v-slot:append>
        <v-text-field
          v-model="slider"
          class="mt-0 pt-0"
          hide-details
          single-line
          type="number"
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
