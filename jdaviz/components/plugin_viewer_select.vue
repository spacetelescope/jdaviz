<template>
  <div>
  <v-row v-if="items.length > 1">
    <v-select
      :items="items"
      v-model="selected"
      @change="$emit('update:selected', $event)"
      :label="label ? label : 'Viewer'"
      :hint="hint ? hint : 'Select viewer.'"
      :rules="rules ? rules : []"
      item-text="ref_or_id"
      item-value="ref_or_id"
      persistent-hint
    >
    <template slot="selection" slot-scope="data">
      <div class="single-line">
        <span>
          {{ data.item.ref_or_id }}
        </span>
      </div>
    </template>
    <template slot="item" slot-scope="data">
      <div class="single-line">
        <span>
          {{ data.item.ref_or_id }}
        </span>
      </div>
    </template>
    </v-select>
  </v-row>
  </div>
</template>

<script>
module.exports = {
  props: ['items', 'selected', 'label', 'hint', 'rules']
};
</script>

<style>
  .single-line {
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
  }
</style>
