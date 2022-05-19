<template>
  <div v-if="sync.in_subscribed_states" style="display: grid"> <!-- overlay container -->
    <div style="grid-area: 1/1">
      <v-row class="row-no-outside-padding">
        <v-col :cols="multiselect ? '8' : '12'" style="padding: 0">
          <div style="grid-area: 1/1">
            <slot></slot>
          </div>
        </v-col>
        <v-col v-if="multiselect" cols="4" style="text-align: center; padding: 0">
          <v-icon v-for="icon in sync.icons">{{icon}}</v-icon>
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
               background-color: rgb(0 0 0 / 20%)">
        <v-icon large dark>mdi-link-off</v-icon>
      </div> 
    </j-tooltip>
  </div>
</template>

<script>
module.exports = {
  props: ['sync', 'multiselect']
};
</script>
