<template>
  <div>
  <v-row v-if="items.length > 1 || show_if_single_entry">
    <v-select
      :menu-props="{ left: true }"
      attach
      :items="items"
      v-model="selected"
      @change="$emit('update:selected', $event)"
      :label="label ? label : 'Subset'"
      :hint="hint ? hint : 'Select subset.'"
      :rules="rules ? rules : []"
      item-text="label"
      item-value="label"
      persistent-hint
    >
      <template slot="selection" slot-scope="data">
        <div class="single-line">
          <v-icon v-if="data.item.color" left :color="data.item.color">
            {{ data.item.type=='spectral' ? 'mdi-chart-bell-curve' : 'mdi-chart-scatter-plot' }}
          </v-icon>
          <span>
            {{ data.item.label }}
          </span>
        </div>
      </template>
      <template slot="item" slot-scope="data">
        <div class="single-line">
          <v-icon v-if="data.item.color" left :color="data.item.color">
            {{ data.item.type=='spectral' ? 'mdi-chart-bell-curve' : 'mdi-chart-scatter-plot' }}
          </v-icon>
          <span>
            {{ data.item.label }}
          </span>
        </div>
      </template>
    </v-select>
  </v-row>
  <v-row v-if="has_subregions_warning && has_subregions">
    <span class="v-messages v-messages__message text--secondary" style="color: red !important">
        {{ has_subregions_warning }}
    </span>
  </v-row>
  </div>
</template>

<script>
module.exports = {
  props: ['items', 'selected', 'label', 'has_subregions', 'has_subregions_warning', 'hint', 'rules', 'show_if_single_entry']
};
</script>

<style>
.v-select__selections {
  flex-wrap: nowrap !important;
}
  .single-line {
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
  }
</style>
