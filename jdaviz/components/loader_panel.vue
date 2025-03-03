<template>
  <div>
    <v-select
      :menu-props="{ left: true }"
      attach
      :items="loader_items_filtered"
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

    <span v-if="loader_selected.length && api_hints_enabled" class="api-hint" style="font-weight: bold; padding-left: 6px">
      ldr = {{ api_hints_obj }}.loaders['{{ loader_selected }}']
    </span>

    <jupyter-widget v-if="loader_selected" :widget="loader_items.find((loader) => loader.name === loader_selected).widget"></jupyter-widget>

  </div>
</template>

<script>
module.exports = {
  props: ['loader_items', 'loader_selected', 'api_hints_enabled', 'api_hints_obj'],
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