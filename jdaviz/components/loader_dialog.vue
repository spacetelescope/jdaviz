<template>
  <div>
    <v-tabs v-model="loader_tab" vertical>
      <v-tab
        v-for="loader in loader_items_filtered"
        :key="loader.name"
      >
      {{loader.name}}
      </v-tab>
      <v-tab-item
        v-for="loader in loader_items_filtered"
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
  computed: {
    loader_items_filtered() {
      var has_api_support = this.checkNotebookContext();
      return this.loader_items.filter(item => {return !item.requires_api_support || has_api_support});
    },
  },
  methods: {
    checkNotebookContext() {
      this.notebook_context = document.getElementById("ipython-main-app")
        || document.querySelector('.jp-LabShell')
        || document.querySelector(".lm-Widget#main"); /* Notebook 7 */
      return this.notebook_context;
    },
  }
}
</script>

<style scoped>
.v-slide-group__wrapper {
  width: 150px;
}
</style>