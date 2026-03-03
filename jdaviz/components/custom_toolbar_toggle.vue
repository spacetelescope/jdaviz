<template>
  <v-row>
    <j-tooltip :tooltipcontent="enabled ? 'Disable' : 'Enable' + ' ' + text">
      <v-btn
        :color="enabled ? 'accent' : 'default'"
        :outlined="!enabled"
        @click="$emit('toggle-custom-toolbar')"
      >
        <slot></slot>
        <span v-if="api_hints_enabled && api_hint_enable" class="api-hint">
          {{ enabled ? api_hint_disable : api_hint_enable }}
        </span>
        <span v-else>
          {{ (enabled ? 'Disable' : 'Enable') + ' ' + text }}
        </span>
      </v-btn>
    </j-tooltip>
  </v-row>
</template>

<script>
  module.exports = {
    props: ['enabled', 'text', 'api_hints_enabled', 'api_hint_enable', 'api_hint_disable']
  };
</script>