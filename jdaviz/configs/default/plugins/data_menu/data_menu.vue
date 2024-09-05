<template>
  <div>
    <div v-if="Object.keys(viewer_icons).length > 1" class="viewer-label invert-if-dark">
      <j-tooltip span_style="white-space: nowrap">
        <j-layer-viewer-icon span_style="float: right;" :icon="viewer_icons[viewer_id]"></j-layer-viewer-icon>
      </j-tooltip>
      <span class="invert-if-dark" style="margin-left: 24px; margin-right: 32px; line-height: 24px">{{viewer_reference || viewer_id}}</span>
    </div>

    <div v-for="(layer_info, layer_name) in visible_layers" class="viewer-label invert-if-dark">
      <j-tooltip span_style="white-space: nowrap">
        <j-layer-viewer-icon span_style="float: right;" :icon="layer_icons[layer_name]" :linewidth="layer_info.linewidth" :linestyle="'solid'" :color="layer_info.color"></j-layer-viewer-icon>
      </j-tooltip>
      <span class="invert-if-dark" style="margin-left: 24px; margin-right: 32px; line-height: 24px">
        <v-icon v-if="layer_info.prefix_icon" dense>
          {{layer_info.prefix_icon}}
        </v-icon>
        {{layer_name}}
      </span>
    </div>
  </div>
</template>

<style scoped>
  .viewer-label {
    display: block;
    float: right;
    background-color: #c3c3c3c3;
    width: 24px;
    overflow: hidden;
    white-space: nowrap;
    /*cursor: pointer;*/
  }
  .viewer-label:last-child {
    padding-bottom: 2px;
  }
  .viewer-label:hover {
    background-color: #e5e5e5;
    width: auto;
    border-bottom-left-radius: 4px; 
    border-top-left-radius: 4px;
  }
</style>