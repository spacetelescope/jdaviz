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
      <v-select
        class="pl-md-4 no-hint"
        style="min-width: 125px"
        :items="['Redshift', 'RV (km/s)']"
        v-model="slider_type"
        dense>
      </v-select>
    </template>
    <template v-slot:append>
        <v-text-field
          v-model="slider_textbox"
          @change="parseTextInput"
          class="mt-0 pt-0"
          style="min-width: 80px"
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
        (v) => { 
          this.slider = v
        },
        this.wait);
      this.parseTextInput = (v) => {
        // strip non-numeric entries and convert to valid float
        this.slider_textbox = parseFloat(String(v).replace(/[^\d.-]/g, ''));
      }
    },
  }
</script>

<style lang="sass">
  $slider-transition: none !important
</style>
