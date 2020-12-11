<template>
  <!-- <v-toolbar-items> -->
  <!-- <v-divider vertical></v-divider> -->
  <div>
    <v-row>
      <v-select 
        :items="['Redshift', 'RV (km/s)']"
        v-model="slider_type">
      </v-select>
    </v-row>
    <v-row>
    <v-slider
      :value="slider"
      @input="throttledSetValue"
      class="align-center"
      :max="max_value"
      :min="min_value"
      hide-details
      style="max-width: 33%; min-width: 300px"
      label="Redshift"
      :step="slider_step"
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
          :step="slider_step"
        ></v-text-field>
      </template>
    </v-slider>
    </v-row>
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
