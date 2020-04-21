<template>
  <!-- <v-toolbar-items> -->
  <!-- <v-divider vertical></v-divider> -->
  <div>
    <v-slider
      v-model="slider"
      class="align-center"
      :max="max_value"
      :min="min_value"
      hide-details
      style="max-width: 33%; min-width: 300px"
      label="Slice"
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
    <!-- the below is temporarily hidden because of spacing issues, which will be adjusted in a future PR that makes more substantial changes to the UI layout -->
    <v-checkbox v-show="false" v-model="linked" label="Linked"></v-checkbox>
  </div>
  <!-- </v-toolbar-items> -->
</template>

<style lang="sass">
  $slider-transition: none !important
</style>
