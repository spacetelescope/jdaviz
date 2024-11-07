<template>
  <j-tooltip v-if="subset_type == 'spatial'" span_style="display: inline-block" tooltipcontent="Spatial subset">
    <v-icon dense>
      mdi-chart-scatter-plot
    </v-icon>
  </j-tooltip>
  <j-tooltip v-else-if="subset_type == 'spectral'" span_style="display: inline-block" tooltipcontent="Spectral subset">
   <v-icon dense>
      mdi-chart-bell-curve
    </v-icon>
  </j-tooltip>
  <j-tooltip v-else-if="subset_type == 'temporal'" span_style="display: inline-block" tooltipcontent="Temporal subset">
    <v-icon dense>
      mdi-chart-line
    </v-icon>
  </j-tooltip>
</template>

<script>
  module.exports = {
    props: ['subset_type']
  };
</script>