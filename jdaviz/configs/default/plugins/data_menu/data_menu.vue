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
          @click="() => {data_menu_open = !data_menu_open}"
        />
      </span>
      <span class="invert-if-dark" style="margin-left: 30px; margin-right: 36px; line-height: 28px">{{viewer_reference || viewer_id}}</span>
    </div>

    <div v-for="item in layer_items.slice().reverse()" class="viewer-label">
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
            @click="() => {data_menu_open = !data_menu_open}"
          />
        </span>
        <span class="invert-if-dark" style="margin-left: 30px; margin-right: 36px; line-height: 28px">
          <v-icon v-if="item.subset_type == 'spatial'" dense>
            mdi-chart-scatter-plot
          </v-icon>
          <v-icon v-else-if="item.subset_type == 'spectral'" dense>
            mdi-chart-bell-curve
          </v-icon>
          <v-icon v-else-if="item.subset_type == 'temporal'" dense>
            mdi-chart-line
          </v-icon>
          {{item.label}}
        </span>
      </div>
    </div>

    <div 
      v-if="data_menu_open" 
      style="position: absolute; float: right; right: 32px; top: 2px; background-color: white; border: 2px solid black; width: 250px; height: 350px"
    >
      <span>
        <b> {{ viewer_id }}</b>
      </span>
      <br/>
      <span v-for="layer in layer_items">
        {{ layer.label }}<br/>
      </span>
    </div>

  </div>
</template>

<script>
  module.exports = {
    data: function () {
      return {
        data_menu_open: false,
      }
    },
    methods: {
      onScroll(e) {
        const dataMenuHeight = document.getElementById(`menu-button-${this.viewer_id}`).parentElement.getBoundingClientRect().height
        const top = document.getElementById(`target-${this.viewer_id}`).getBoundingClientRect().y + document.body.parentElement.scrollTop + dataMenuHeight;
        if (this.data_menu_open && document.getElementById(`target-${this.viewer_id}`)) {
          const menuContent = document.getElementById(`menu-content-${this.viewer_id}`);
          menuContent.parentElement.style.top = top + "px";
        }
      }
    },
  }
</script>

<style scoped>
  .viewer-label {
    display: block;
    float: right;
    background-color: #c3c3c32c;
    width: 30px;
    overflow: hidden;
    white-space: nowrap;
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