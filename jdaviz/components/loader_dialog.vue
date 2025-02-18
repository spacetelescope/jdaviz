<template>
  <div>
    <v-tabs v-model="loader_tab" vertical>
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
  </div>
</template>

<script>
module.exports = {
  props: ['loader_items', 'loader_tab', 'api_hints_enabled', 'config'],
}
</script>

<style scoped>
.v-slide-group__wrapper {
  width: 150px;
}
</style>