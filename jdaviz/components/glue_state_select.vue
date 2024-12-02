<template>
  <v-select
    attach
    :menu-props="{ left: true }"
    :items="items"
    v-model="selected"
    @change="$emit('update:selected', $event)"
    :label="api_hints_enabled && api_hint ? api_hint : label"
    :class="api_hints_enabled && api_hint ? 'api-hint no-hint' : 'no-hint'"
    dense
  >
    <template v-slot:selection="{ item, index }">
      <span :class="api_hints_enabled ? 'api-hint' : null">
        {{ api_hints_enabled ?
          '\'' + item.text + '\''
          :
          item.text
        }}
      </span>
    </template>
  </v-select>
</template>

<script>
module.exports = {
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
