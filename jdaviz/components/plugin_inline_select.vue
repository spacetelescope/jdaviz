<template>
  <div>
    <j-flex-row v-if="api_hints_enabled && api_hint">
      <span class="api-hint">
        {{ api_hint }}
      </span>
    </j-flex-row>
    <j-flex-row v-for="item in items" class="row-min-bottom-padding">
      <plugin-inline-select-item
        :item="item"
        :selected="selected"
        @update:selected="$emit('update:selected', $event)"
        :multiselect="multiselect"
        :single_select_allow_blank="single_select_allow_blank"
        :api_hints_enabled="api_hints_enabled"
      ></plugin-inline-select-item>
    </j-flex-row>
  </div>
</template>

<script>
export default {
  props: ['items', 'selected', 'multiselect', 'single_select_allow_blank', 'api_hint', 'api_hints_enabled']
};
</script>

<style scoped>
</style>
