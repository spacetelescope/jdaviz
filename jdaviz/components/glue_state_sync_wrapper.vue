<template>
  <div v-if="sync.in_subscribed_states" style="display: grid; padding-top: 4px; padding-bottom: 4px"> <!-- overlay container -->
    <v-row no-gutters align="center" style="grid-area: 1/1">
      <v-col :cols="multiselect ? 8 : 12">
        <slot></slot>
      </v-col>
      <v-col v-if="multiselect" cols="4" class="text-center">
        <j-layer-viewer-icon v-for="icon in sync.icons" :icon="icon" :prevent_invert_if_dark="true"></j-layer-viewer-icon>
      </v-col>
    </v-row>
    <j-tooltip v-if="sync.mixed" tipid='plugin-plot-options-mixed-state' span_style="display: grid; grid-area: 1/1">
      <div
        @click="() => {$emit('unmix-state')}"
        class="text-center"
        style="z-index:2;
               margin-left: -24px;
               margin-right: -24px;
               cursor: pointer;
               border: 2px solid #00617E;
               background-color: rgb(245 245 245 / 70%);">
        <v-icon
          large
          color="#00617E"
          style="height: 100%"
        >mdi-link-off</v-icon>
      </div>
    </j-tooltip>
  </div>
</template>

<script>
export default {
  props: ['sync', 'multiselect']
};
</script>
