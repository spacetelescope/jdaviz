<template>
  <!-- <v-toolbar-items> -->
    <!-- <v-divider vertical></v-divider> -->
    <v-slider
      v-model="slider"
      class="align-center"
      :max="max_value"
      :min="min_value"
      hide-details
      @end="on_slider_updated"
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
          @change="on_slider_updated"
          filled
          dense
        ></v-text-field>
      </template>
    </v-slider>
  <!-- </v-toolbar-items> -->
</template>