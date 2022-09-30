<template>
  <div>
  <v-row v-if="items.length > 1 || show_if_single_entry">
    <v-select
      :menu-props="{ left: true }"
      attach
      :items="items"
      v-model="selected"
      @change="$emit('update:selected', $event)"
      :label="label ? label : 'Data'"
      :hint="hint ? hint : 'Select data.'"
      :rules="rules ? rules : []"
      item-text="label"
      item-value="label"
      persistent-hint
    >
    <template slot="selection" slot-scope="data">
      <div class="single-line">
        <span>
          <j-layer-viewer-icon v-if="data.item.icon" span_style="margin-right: 4px" :icon="data.item.icon" :prevent_invert_if_dark="true"></j-layer-viewer-icon>
          {{ data.item.label }}
        </span>
      </div>
    </template>
    <template slot="item" slot-scope="data">
      <div class="single-line">
        <span>
          <j-layer-viewer-icon v-if="data.item.icon" span_style="margin-right: 4px" :icon="data.item.icon" :prevent_invert_if_dark="true"></j-layer-viewer-icon>
          {{ data.item.label }}
        </span>
      </div>
    </template>
   </v-select>
  </v-row>
 </div>
</template>
<script>
module.exports = {
  props: ['items', 'selected', 'label', 'hint', 'rules', 'show_if_single_entry']
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
