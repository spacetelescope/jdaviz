<template>
  <div>
    <v-row v-for="item in items" class="row-min-bottom-padding">
      <plugin-inline-select-item
        :item="item"
        :selected.sync="selected"
        @update:selected="$emit('update:selected', $event)"
        :multiselect="multiselect"
        :single_select_allow_blank="single_select_allow_blank"
      ></plugin-inline-select-item>
    </v-row>
  </div>
</template>

<script>
module.exports = {
  props: ['items', 'selected', 'multiselect', 'single_select_allow_blank']
};
</script>

<style scoped>
</style>
