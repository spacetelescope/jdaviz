<template>
  <v-switch
    :label="api_hints_enabled && api_hint ? api_hint+' '+boolToString(value) : label"
    :class="api_hints_enabled && api_hint ? 'api-hint' : null"
    :hint="hint"
    v-model="value"
    @change="$emit('update:value', $event)"
    persistent-hint>
  </v-switch>
</template>

<script>
  module.exports = {
    props: ['value', 'label', 'hint', 'api_hint', 'api_hints_enabled'],
    methods: {
      boolToString(b) {
        if (b) {
          return 'True'
        } else {
          return 'False'
        }
      },
    }
  };
</script>
