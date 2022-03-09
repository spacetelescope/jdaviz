<template>
  <v-select
    :items="spectral_subset_items"
    v-model="selected_subset"
    @change="$emit('update:selected_subset', $event)"
    :label="label ? label : 'Spectral Region'"
    :hint="hint ? hint : 'Select spectral region.'"
    item-text="label"
    item-value="label"
    persistent-hint
  >
    <template slot="selection" slot-scope="data">
      <div class="single-line">
        <v-icon v-if="data.item.color" left :color="data.item.color">
          mdi-chart-bell-curve
        </v-icon>
        <span>
          {{ data.item.label }}
        </span>
      </div>
    </template>
    <template slot="item" slot-scope="data">
      <div class="single-line">
        <v-icon v-if="data.item.color" left :color="data.item.color">
          mdi-chart-bell-curve
        </v-icon>
        <span>
          {{ data.item.label }}
        </span>
      </div>
    </template>
  </v-select>
</template>

<script>
module.exports = {
  props: ['spectral_subset_items', 'selected_subset', 'label', 'hint']
};
</script>

<style>
  .single-line {
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
  }
</style>
