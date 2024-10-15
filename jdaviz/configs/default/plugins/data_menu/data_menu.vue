<template>
  <div>
    <div v-if="Object.keys(viewer_icons).length > 1" class="viewer-label">
      <span style="float: right;">
        <j-layer-viewer-icon-stylized
          tooltip=""
          :label="viewer_id"
          :icon="viewer_icons[viewer_id]"
          :visible="true"
          :is_subset="false"
          :colors="['#939393']"
          :linewidth="0"
          :cmap_samples="cmap_samples"
          btn_style="margin-bottom: 0px"
        />
      </span>
      <span class="invert-if-dark" style="margin-left: 30px; margin-right: 36px; line-height: 28px">{{viewer_reference || viewer_id}}</span>
    </div>

    <div v-for="item in layer_items" class="viewer-label">
      <div v-if="item.visible">
        <span style="float: right;">
          <j-layer-viewer-icon-stylized
            tooltip=""
            :label="item.label"
            :icon="item.icon"
            :visible="item.visible"
            :is_subset="item.is_subset"
            :colors="item.colors"
            :linewidth="item.linewidth"
            :cmap_samples="cmap_samples"
            btn_style="margin-bottom: 0px"
          />
        </span>
        <span class="invert-if-dark" style="margin-left: 30px; margin-right: 36px; line-height: 28px">
          <v-icon v-if="item.prefix_icon" dense>
            {{item.prefix_icon}}
          </v-icon>
          {{item.label}}
        </span>
      </div>
    </div>

  </div>
</template>

<style scoped>
  .viewer-label {
    display: block;
    float: right;
    background-color: #c3c3c32c;
    width: 30px;
    overflow: hidden;
    white-space: nowrap;
    /*cursor: pointer;*/
  }
  .viewer-label:last-child {
    padding-bottom: 0px;
    border-bottom-left-radius: 4px; 
  }
  .viewer-label:hover {
    background-color: #e5e5e5;
    width: auto;

    border-top-left-radius: 4px;
    border-bottom-left-radius: 4px;
  }
</style>