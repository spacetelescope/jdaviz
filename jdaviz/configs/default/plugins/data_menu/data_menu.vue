<template>
  <div>
    <v-menu offset-x left :close-on-content-click="false" v-model="data_menu_open">
      <template v-slot:activator="{ on, attrs }">
        <div>
          <div v-if="Object.keys(viewer_icons).length > 1" :id="'layer-legend-'+ viewer_id" class="viewer-label">
            <span style="float: right;">
              <j-layer-viewer-icon-stylized
                tooltip="View data layers and subsets"
                :label="viewer_id"
                :icon="viewer_icons[viewer_id]"
                :visible="true"
                :is_subset="false"
                :colors="['#939393']"
                :linewidth="0"
                :cmap_samples="cmap_samples"
                btn_style="margin-bottom: 0px"
                @click="() => {if (dev_data_menu) {data_menu_open = !data_menu_open}}"
                :disabled="!dev_data_menu"
              />
            </span>
            <span class="invert-if-dark" style="margin-left: 30px; margin-right: 36px; line-height: 28px">{{viewer_reference || viewer_id}}</span>
          </div>

          <div v-for="item in layer_items.slice().reverse()" class="viewer-label">
            <div v-if="item.visible">
              <span style="float: right;">
                <j-layer-viewer-icon-stylized
                  tooltip="View data layers and subsets"
                  :label="item.label"
                  :icon="item.icon"
                  :visible="item.visible"
                  :is_subset="item.is_subset"
                  :colors="item.colors"
                  :linewidth="item.linewidth"
                  :cmap_samples="cmap_samples"
                  btn_style="margin-bottom: 0px"
                  @click="() => {if (dev_data_menu) {data_menu_open = !data_menu_open}}"
                  :disabled="!dev_data_menu"
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
        </div>
      </template>
      <v-list :id="'dm-content-' + viewer_id" style="max-height: 500px; width: 465px" class="overflow-y-auto">
        <v-list-item class="dm-header">
          <v-list-item-icon>
            <j-tooltip
              tooltipcontent="Reorder layers (COMING SOON)"
            >
              <v-btn
                icon
                disabled
              >
                <v-icon>mdi-format-vertical-align-center</v-icon>
              </v-btn>
            </j-tooltip>
          </v-list-item-icon>
          <v-list-item-content>
            <j-tooltip
              tooltipcontent="Change orientation (COMING SOON)"
            >
              orientation
            </j-tooltip>
          </v-list-item-content>
          <v-list-item-action>
            <j-tooltip tooltipcontent="Add data or subset (COMING SOON)">
              <v-btn
                icon
                disabled
              >
                <v-icon>mdi-plus</v-icon>
              </v-btn>
            </j-tooltip>
          </v-list-item-action>
        </v-list-item>
        <v-list-item-group
          v-model="dm_layer_selected"
          active-class="active-list-item"
          multiple
          dense
        >
          <div>
          <v-list-item v-for="item in layer_items.slice().reverse()">
            <v-list-item-icon>
              <j-layer-viewer-icon-stylized
                  :label="item.label"
                  :icon="item.icon"
                  :visible="item.visible"
                  :is_subset="item.is_subset"
                  :colors="item.colors"
                  :linewidth="item.linewidth"
                  :cmap_samples="cmap_samples"
                  btn_style="margin-bottom: 0px"
                  disabled="true"
                />
            </v-list-item-icon>
            <v-list-item-content>
              {{  item.label }}
            </v-list-item-content>
            <v-list-item-action>
              <j-tooltip tooltipcontent="Toggle visibility">
                <plugin-switch
                  :value="item.visible"
                  @click="(value) => {set_layer_visibility({layer: item.label, value: value})}"
                  :api_hint='"dm.set_layer_visibility("+viewer_id+", "'
                  :api_hints_enabled="false"
                  :use_eye_icon="true"
                />
              </j-tooltip>
            </v-list-item-action>
          </v-list-item>
          </div>
        </v-list-item-group>
        <v-list-item class="dm-footer">
          <v-list-item-content style="display: inline-block">
            <j-tooltip
              span_style="display: inline-block; float: right"
              tooltipcontent="Remove data/subset (COMING SOON)"
            >
              <v-btn
                icon
                disabled
              >
                <v-icon>mdi-delete</v-icon>
              </v-btn>
            </j-tooltip>
            <j-tooltip
              v-if="dm_layer_selected.length == 1 && layer_items[layer_items.length - 1 - dm_layer_selected[0]].icon.length == 1 && !layer_items[layer_items.length - 1 - dm_layer_selected[0]].is_subset && !layer_items[layer_items.length - 1 - dm_layer_selected[0]].from_plugin"
              span_style="display: inline-block; float: right"
              tooltipcontent="View Metadata"
            >
              <v-btn
                icon
                disabled
                >
                <v-icon>mdi-label</v-icon>
              </v-btn>
            </j-tooltip>
            <j-tooltip
              span_style="display: inline-block; float: right"
              tooltipcontent="Edit Selected Subset (COMING SOON)"
            >
              <v-btn
                text
                disabled
              >
                Edit Subset
              </v-btn>
            </j-tooltip>
          </v-list-item-content>
        </v-list-item>
      </v-list>
    </v-menu>
    <div :id="'dm-target-' + viewer_id"></div>
  </div>
</template>

<script>
  module.exports = {
    data: function () {
      return {
        data_menu_open: false,
      }
    },
    mounted() {
      let element = document.getElementById(`dm-target-${this.viewer_id}`).parentElement
      if (element === null) {
        return
      }
      while (element["tagName"] !== "BODY") {
        if (["auto", "scroll"].includes(window.getComputedStyle(element).overflowY)) {
          element.addEventListener("scroll", this.onScroll);
        }
        element = element.parentElement;
      }
    },
    beforeDestroy() {
      let element = document.getElementById(`dm-target-${this.viewer_id}`).parentElement
      if (element === null) {
        return
      }
      while (element["tagName"] !== "BODY") {
        if (["auto", "scroll"].includes(window.getComputedStyle(element).overflowY)) {
          element.removeEventListener("scroll", this.onScroll);
        }
        element = element.parentElement;
      }
    },
    methods: {
      onScroll(e) {
        const dataMenuHeight = document.getElementById(`layer-legend-${this.viewer_id}`).parentElement.getBoundingClientRect().height
        const top = document.getElementById(`dm-target-${this.viewer_id}`).getBoundingClientRect().y + document.body.parentElement.scrollTop + dataMenuHeight;
        if (this.data_menu_open && document.getElementById(`dm-target-${this.viewer_id}`)) {
          const menuContent = document.getElementById(`dm-content-${this.viewer_id}`);
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
  .v-list {
    padding-top: 0px !important;
    padding-bottom: 0px !important;
  }
  .v-list-item__icon, .v-list-item__content, .v-list-item__action {
    /* even denser than dense */
    padding-top: 4px !important;
    padding-bottom: 4px !important;
    margin-top: 2px !important;
    margin-bottom: 2px !important;
  }
  .v-list-item__icon {
    margin-top: 6px !important;
  }
  .v-list-item:nth-child(even) {
    /* alternating row colors */
    background-color: #f1f2f8;
  }
  .active-list-item {
    background-color: #d1f4ff !important;
  }
  .dm-header, .dm-footer {
    background-color: #003B4D;
    color: white !important;
    font-weight: bold;
  }
  i.dm-header, i.dm-footer {
    color: white !important;
  }
  .dm-header.v-btn--disabled  .v-icon {
    color: green !important;
  }
</style>