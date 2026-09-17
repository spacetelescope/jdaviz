<template>
  <j-flex-row>
    <j-tooltip :tooltipcontent="enabled ? 'Disable' : 'Enable' + ' ' + text">
      <v-btn
        :color="enabled ? 'accent' : 'default'"
        :outlined="!enabled"
        @click="$emit('toggle-custom-toolbar')"
      >
        <slot></slot>
        <span v-if="api_hints_enabled && api_hint_enable" :class="enabled ? 'api-hint api-hint-invert-color' : 'api-hint'">
          {{ enabled ? api_hint_disable : api_hint_enable }}
        </span>
        <span v-else>
          {{ (enabled ? 'Disable' : 'Enable') + ' ' + text }}
        </span>
      </v-btn>
    </j-tooltip>
  </j-flex-row>
</template>

<script>
  export default {
    props: ['enabled', 'text', 'api_hints_enabled', 'api_hint_enable', 'api_hint_disable']
  };
</script>
