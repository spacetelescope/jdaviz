<template>
  <div>
    <v-tabs v-if='use_tabs' v-model="loader_selected" vertical>
      <v-tab
        v-for="loader in loader_items"
        :key="loader.name"
      >
      {{loader.name}}
      </v-tab>
      <v-tab-item
        v-for="loader in loader_items"
        :key="loader.name"
      >
        <span v-if="api_hints_enabled" class="api-hint" style="font-weight: bold">loader = {{  config }}.loaders['{{ loader.name }}']</span>
        <jupyter-widget :widget="loader.widget" :key="loader.name" class="loader-in-dialog"></jupyter-widget>
      </v-tab-item>
    </v-tabs>
    <div v-else>
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

    <div>
  </div>
</template>

<script>
module.exports = {
  props: ['loader_items', 'loader_selected', 'api_hints_enabled', 'config', 'use_tabs'],
}
</script>

<style scoped>
.v-slide-group__wrapper {
  width: 150px;
}
</style>