<template>
  <span v-if="use_eye_icon">
    <v-btn
      icon 
      @mouseover="$emit('mouseover')"
      @mouseleave="$emit('mouseleave')"
      @click.stop="$emit('update:value', !value); $emit('click', !value)"
    >
      <v-icon>mdi-eye{{ value ? '' : '-off' }}</v-icon>
    </v-btn>
    <span v-if="api_hints_enabled && api_hint" class="api-hint">
      {{ api_hint + boolToString(value) }}
    </span>
    <span v-else>
      {{ label }}
    </span>
  </span>
  <v-switch
    v-else
    :label="api_hints_enabled && api_hint ? api_hint+' '+boolToString(value) : label"
    :class="api_hints_enabled && api_hint ? 'api-hint' : null"
    :hint="hint"
    v-model="value"
    @change="$emit('update:value', $event); $emit('click', $event)"
    persistent-hint>
  </v-switch>
</template>

<script>
  module.exports = {
    props: ['value', 'label', 'hint', 'api_hint', 'api_hints_enabled', 'use_eye_icon'],
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
