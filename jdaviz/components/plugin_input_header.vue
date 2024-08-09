<template>
  <v-subheader
    :class="api_hints_enabled ? 'pl-0 slider-label api-hint' : 'pl-0 slider-label'"
    style="height: 12px"
  >
    {{ api_hints_enabled && api_hint ?
      api_hint
      :
      label
    }}
  </v-subheader>
</template>

<script>
  module.exports = {
    props: ['label', 'api_hint', 'api_hints_enabled'],
  };
</script>
