<template>
  <j-tooltip
    :tooltipcontent="'sublayer of '+icon[0].toUpperCase()"
    span_style="display: inline-block" 
  >
 <v-icon>mdi-layers-outline</v-icon>
  </j-tooltip>
</template>

<script>
  export default {
    props: ['icon']
  };
</script>