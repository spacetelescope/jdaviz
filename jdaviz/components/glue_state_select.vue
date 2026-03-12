<template>
  <v-select
    attach
    :menu-props="{ left: true }"
    :items="items"
    :model-value="selected"
    @update:modelValue="$emit('update:selected', $event)"
    :label="api_hints_enabled && api_hint ? api_hint : label"
    :class="api_hints_enabled && api_hint ? 'api-hint no-hint' : 'no-hint'"
    density="compact"
  >
    <template v-slot:selection="{ item, index }">
      <span :class="api_hints_enabled ? 'api-hint' : null">
        {{ api_hints_enabled ?
          '\'' + item.raw.text + '\''
          :
          item.raw.text
        }}
      </span>
    </template>
  </v-select>
</template>

<script>
export default {
  props: ['items', 'selected', 'label', 'api_hint', 'api_hints_enabled']
};
</script>

<style scoped>
  .v-select__selections {
    flex-wrap: nowrap !important;
    display: block !important;
    margin-bottom: -32px;
  }
</style>
