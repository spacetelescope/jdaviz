<template>
  <v-row>
    <j-tooltip :tooltipcontent="enabled ? 'Disable' : 'Enable' + ' ' + text">
      <v-btn
        :color="enabled ? 'accent' : 'default'"
        :outlined="!enabled"
        @click="$emit('toggle-custom-toolbar')"
      >
        <slot></slot>
        {{ enabled ? 'Disable' : 'Enable' }} {{ text }}
      </v-btn>
    </j-tooltip>
  </v-row>
</template>

<script>
  module.exports = {
    props: ['enabled', 'text']
  };
</script>