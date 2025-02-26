<template>
  <div>
    <v-select
      :menu-props="{ left: true }"
      attach
      :items="loader_items"
      v-model="loader_selected"
      @change="$emit('update:loader_selected', $event)"
      label="Source"
      hint="Select source to get data"
      item-text="name"
      item-value="name"
      persistent-hint
      outlined
      style="width: 100%; margin-top: 12px; padding-left: 6px; padding-right: 6px;"
    ></v-select>

    <jupyter-widget v-if="loader_selected" :widget="loader_items.find((loader) => loader.name === loader_selected).widget"></jupyter-widget>

  </div>
</template>

<script>
module.exports = {
  props: ['loader_items', 'loader_selected', 'api_hints_enabled', 'config'],
}
</script>

<style scoped>
.v-slide-group__wrapper {
  width: 150px;
}
</style>