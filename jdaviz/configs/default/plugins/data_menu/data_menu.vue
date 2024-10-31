<template>
  <div>
    <v-menu
      offset-x
      left
      nudge-left="8"
      transition="slide-x-reverse-transition"
      :close-on-content-click="false"
      v-model="data_menu_open">
      <template v-slot:activator="{ on, attrs }">
        <div :id="'layer-legend-'+ viewer_id">
          <div v-if="Object.keys(viewer_icons).length > 1 || Object.keys(visible_layers).length == 0 || data_menu_open" class="viewer-label"> 
            <span style="float: right;">
              <j-layer-viewer-icon-stylized
                :tooltip="data_menu_open ? 'close menu' : 'View data layers and subsets'"
                :label="viewer_id"
                :icon="data_menu_open ? 'mdi-close' : viewer_icons[viewer_id]"
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
                <j-subset-icon :subset_type="item.subset_type" />
                {{item.label}}
              </span>
            </div>
          </div>
        </div>
      </template>
      <v-list :id="'dm-content-' + viewer_id" style="width: 400px" class="overflow-y-auto">
        <v-list-item class="dm-header">
          <v-list-item-icon>
            <j-tooltip
              tooltipcontent="Reorder layers (COMING SOON)"
            >
              <v-btn
                icon
                disabled
              >
                <v-icon class="invert-if-dark">mdi-format-vertical-align-center</v-icon>
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
            <data-menu-add-data
              :dataset_items="dataset_items"
              :subset_tools="subset_tools"
              @add-data="(data_label) => {add_data_to_viewer({data_label: data_label})}"
              @create-subset="(subset_type) => {create_subset({subset_type: subset_type}); data_menu_open = false}"
            >
            </data-menu-add-data>
          </v-list-item-action>
        </v-list-item>
        <v-list-item-group
          v-model="dm_layer_selected"
          active-class="active-list-item"
          style="max-height: 265px; overflow-y: auto;"
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
              <span style="display: inline-block">
                <j-subset-icon v-if="item.subset_type" :subset_type="item.subset_type" />
                <j-tooltip
                  v-if="item.icon.length == 2"
                  :tooltipcontent="'sublayer of '+item.icon[0].toUpperCase()"
                  span_style="display: inline-block" 
                >
                  <v-icon dense>mdi-layers-outline</v-icon>
                </j-tooltip>
                {{  item.label }}
              </span>
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
            <data-menu-remove
              :delete_enabled="delete_enabled"
              :delete_tooltip="delete_tooltip"
              @remove-from-viewer="remove_from_viewer"
              @remove-from-app="remove_from_app"
            />
            <j-tooltip
              :span_style="'display: inline-block; float: right; ' + (info_enabled ? '' : 'cursor: default;')"
              :tooltipcontent="info_tooltip"
            >
              <v-btn
                icon
                @click="view_info"
                :disabled="!info_enabled"
              >
                <v-icon class="invert-if-dark">mdi-label</v-icon>
              </v-btn>
            </j-tooltip>
            <data-menu-subset-edit
              :subset_edit_enabled="subset_edit_enabled"
              :subset_edit_tooltip="subset_edit_tooltip"
              :selected_n_subsets="selected_n_subsets"
              @view-info="view_info"
            />
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
    background-color: #f1f2f85a;
  }
  .active-list-item {
    background-color: #d1f4ff75 !important;
    font-weight: 500;
  }
  .dm-header, .dm-footer {
    background-color: #003B4D;
    font-weight: bold;
  }
  .dm-header > .v-list-item__icon, .dm-header > .v-list-item__content, .dm-header > .v-list-item__action,
  .dm-footer > .v-list-item__icon, .dm-footer > .v-list-item__content, .dm-footer > .v-list-item__action {
    filter: invert(1);
  }

  .dm-header.v-btn--disabled  .v-icon {
    color: green !important;
  }
</style>