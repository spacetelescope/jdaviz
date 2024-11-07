<template>
  <j-tooltip
    :tooltipcontent="'sublayer of '+icon[0].toUpperCase()"
    span_style="display: inline-block" 
  >
    <v-icon dense>mdi-layers-outline</v-icon>
  </j-tooltip>
</template>

<script>
  module.exports = {
    props: ['icon']
  };
</script>