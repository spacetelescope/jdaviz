<template>
  <div>
    <v-select
      v-if="!hide_resolver"
      :menu-props="{ left: true }"
      attach
      :items="loader_items_filtered"
      :model-value="loader_selected"
      @update:modelValue="$emit('update:loader_selected', $event)"
      label="Source"
      hint="Select source to get data"
      item-title="name"
      item-value="name"
      persistent-hint
      variant="outlined"
      style="width: 100%; margin-top: 12px; padding-left: 6px; padding-right: 6px;"
    ></v-select>

    <span v-if="loader_selected && loader_selected.length && (api_hints_enabled || (loader_selected === 'object' && !hide_resolver))" class="api-hint" style="font-weight: bold; padding-left: 6px">
      ldr = {{ api_hints_obj }}.loaders['{{ loader_selected }}']
    </span>

    <jupyter-widget v-if="selected_loader_widget" :widget="selected_loader_widget" :key="selected_loader_widget"></jupyter-widget>

  </div>
</template>

<script>
export default {
  props: ['loader_items', 'loader_selected', 'api_hints_enabled', 'api_hints_obj', 'server_is_remote', 'disabled_loaders', 'hide_resolver'],
  computed: {
    loader_items_filtered() {
      var has_api_support = this.checkNotebookContext();
      // Determine which loaders to disable
      var disabled_loaders = this.disabled_loaders;
      if (disabled_loaders === null || disabled_loaders === undefined) {
        // Default: disable loaders based on server_is_remote setting
        if (this.server_is_remote) {
          disabled_loaders = ['file', 'file drop', 'url', 'object',
                              'astroquery', 'virtual observatory'];
        } else {
          disabled_loaders = [];
        }
      }
      return this.loader_items.filter(item => {
        return (!item.requires_api_support || has_api_support) &&
               !disabled_loaders.includes(item.name);
      });
    },
    selected_loader_widget() {
      const loader = this.loader_items.find(item => item.name === this.loader_selected);
      return loader ? loader.widget : '';
    },
  },
  watch: {
    loader_items_filtered: {
      handler(newFiltered) {
        // If the currently selected loader is not in the filtered list,
        // select the first available item
        if (newFiltered.length > 0) {
          const isCurrentInFiltered = newFiltered.some(item => item.name === this.loader_selected);
          if (!isCurrentInFiltered) {
            this.$emit('update:loader_selected', newFiltered[0].name);
          }
        }
      },
      immediate: true
    }
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
