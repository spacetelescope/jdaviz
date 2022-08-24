<template>
  <div v-if="sync.in_subscribed_states" style="display: grid; padding-top: 4px; padding-bottom: 4px"> <!-- overlay container -->
    <div style="grid-area: 1/1">
      <v-row class="row-no-outside-padding">
        <v-col :cols="multiselect ? '8' : '12'" style="padding: 0">
          <div style="grid-area: 1/1">
            <slot></slot>
          </div>
        </v-col>
        <v-col v-if="multiselect" cols="4" style="text-align: center; padding: 0">
          <j-layer-viewer-icon v-for="icon in sync.icons" :icon="icon" :prevent_invert_if_dark="true"></j-layer-viewer-icon>
        </v-col>
      </v-row>
    </div>
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
          dark
          color="#00617E"
          style="height: 100%"
          >mdi-link-off</v-icon>
      </div> 
    </j-tooltip>
  </div>
</template>

<script>
module.exports = {
  props: ['sync', 'multiselect']
};
</script>
