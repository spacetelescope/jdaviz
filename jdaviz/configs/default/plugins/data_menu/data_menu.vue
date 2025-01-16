<template>
  <div :style="loaded_n_data === 0 ? 'height: 100%' : ''">
    <div class="viewer-label-container">
      <div>
        <v-menu
          offset-x
          left
          nudge-left="8"
          transition="slide-x-reverse-transition"
          :close-on-content-click="false"
          v-model="data_menu_open">
          <template v-slot:activator="{ on, attrs }">
            <div :id="'layer-legend-'+ viewer_id" class="layer-legend">
              <div 
                v-if="Object.keys(viewer_icons).length > 1 || Object.keys(visible_layers).length == 0 || data_menu_open"
                :class="loaded_n_data === 0 && !data_menu_open ? 'viewer-label pulse' : 'viewer-label'"
              > 
                <span style="float: right">
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
                    @click="() => {data_menu_open = !data_menu_open}"
                  />
                </span>
                <span class="invert-if-dark" style="margin-left: 30px; margin-right: 36px; line-height: 28px">{{viewer_reference || viewer_id}}</span>
              </div>

              <div v-for="item in layer_items" class="viewer-label">
                <div v-if="item.visible">
                  <span style="float: right">
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
                      @click="() => {data_menu_open = !data_menu_open}"
                    />
                  </span>
                  <span class="invert-if-dark" style="margin-left: 30px; margin-right: 36px; line-height: 28px">
                    <j-subset-icon v-if="item.subset_type" :subset_type="item.subset_type" />
                    <j-child-layer-icon v-if="/\d/.test(item.icon)" :icon="item.icon" />
                    <j-plugin-live-results-icon v-if="item.live_plugin_results" />
                    {{ item.label }}
                  </span>
                </div>
              </div>
            </div>
          </template>
          <v-list :id="'dm-content-' + viewer_id" style="width: 400px" class="overflow-y-auto">
            <v-list-item v-if="api_hints_enabled" style="min-height: 12px"> 
              <v-list-item-content> 
                <span class="api-hint"> 
                  <b>dm = {{ config }}.viewers['{{viewer_id}}'].data_menu</b>
                </span> 
              </v-list-item-content> 
            </v-list-item> 
            <v-list-item class="dm-header">
              <v-list-item-icon>
                <j-tooltip
                  v-if="false"
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
              <v-list-item-content
                v-if="loaded_n_data > 0"
                style="display: inline-block"
              >
                <j-tooltip
                  v-if="orientation_enabled"
                  :tooltipcontent="orientation_align_by_wcs ? 'Open orientation plugin' : 'data is linked by pixel (app-wide).  To choose orientation, open the orientation plugin and link by WCS.'"
                  span_style="display: inline-block"
                  >
                  <span
                    style="cursor: pointer; display: inline-block; height: 100%; vertical-align: bottom;"
                    @click="() => {open_orientation_plugin()}"
                  >
                    <v-icon class="invert-if-dark" style="margin-right: 8px">mdi-compass-outline</v-icon>
                    <label v-if="!orientation_align_by_wcs" style="font-size: 12px; line-height: 20px; color: rgba(0, 0, 0, 0.6); position: absolute; top: -5px">Orientation</label>
                    <span v-if="!orientation_align_by_wcs" class="invert-if-dark" style="position: absolute; margin-top: 12px">linked by pixel</span>
                  </span>
                </j-tooltip>
                <v-select
                  v-if="orientation_enabled && orientation_align_by_wcs && orientation_layer_items.length > 0"
                  dense
                  :items="orientation_layer_items"
                  v-model="orientation_layer_selected"
                  :label="api_hints_enabled ? 'dm.orientation = ' : 'Orientation'" 
                  :class="api_hints_enabled ? 'api-hint api-hint-invert-color' : 'invert-if-dark'" 
                  item-text="label"
                  item-value="label"
                  :hide-details="true"
                  style="padding-top: 8px !important; padding-bottom: 4px !important; display: inline-block; width: 212px"
                >
                  <template slot="selection" slot-scope="data">
                    <div class="single-line" style="width: 100%">
                      <span :class="api_hints_enabled ? 'api-hint api-hint-invert-color' : null">
                        <j-layer-viewer-icon v-if="data.item.icon && !api_hints_enabled" span_style="margin-right: 4px" :icon="data.item.icon" :icons="icons" :prevent_invert_if_dark="true"></j-layer-viewer-icon>
                        {{ api_hints_enabled ?
                          '\'' + data.item.label + '\''
                          :
                          data.item.label
                        }}
                      </span>
                    </div>
                  </template>
                  <template slot="item" slot-scope="data">
                    <div class="single-line">
                      <span>
                        <j-layer-viewer-icon span_style="margin-right: 4px" :icon="data.item.icon" :icons="icons" :prevent_invert_if_dark="true"></j-layer-viewer-icon>
                        {{ data.item.label }}
                      </span>
                    </div>
                  </template>
                </v-select>
              </v-list-item-content>
              <v-list-item-content v-else>
                <span>No data in viewer</span>
              </v-list-item-content>
              <v-list-item-action>
                <data-menu-add
                  :dataset_items="dataset_items"
                  :subset_tools="subset_tools"
                  :loaded_n_data="loaded_n_data"
                  :api_hints_enabled="api_hints_enabled"
                  :icons="icons"
                  @add-data="(data_label) => {add_data_to_viewer({data_label: data_label})}"
                  @create-subset="(subset_type) => {create_subset({subset_type: subset_type}); data_menu_open = false}"
                >
                </data-menu-add>
              </v-list-item-action>
            </v-list-item>
            <v-list-item 
              v-if="api_hints_enabled" 
            > 
              <v-list-item-content> 
                <span class="api-hint">dm.layer = {{ layer_selected }}</span> 
              </v-list-item-content> 
            </v-list-item> 
            <v-list-item-group
              v-model="dm_layer_selected"
              active-class="active-list-item"
              style="max-height: 265px; overflow-y: auto;"
              multiple
              dense
            >
              <div>
              <v-list-item 
                v-for="item in layer_items" 
                class="layer-select" 
              > 
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
                    <j-child-layer-icon v-if="/\d/.test(item.icon)" :icon="item.icon" />
                    <j-plugin-live-results-icon v-if="item.live_plugin_results" />
                    {{ item.label }}
                  </span>
                </v-list-item-content>
                <v-list-item-action>
                  <j-tooltip 
                    :tooltipcontent="api_hints_enabled ? '' : 'Toggle visibility'" 
                  > 
                    <plugin-switch
                      :value="item.visible"
                      @click="(value) => {set_layer_visibility({layer: item.label, value: value})}"
                      @mouseover = "() => {hover_api_hint = 'dm.set_layer_visibility(\'' + item.label + '\', '+boolToString(item.visible)+')'}" 
                      @mouseleave = "() => {if (!lock_hover_api_hint) {hover_api_hint = ''}}"
                      :api_hints_enabled="false"
                      :use_eye_icon="true"
                    />
                  </j-tooltip>
                </v-list-item-action>
              </v-list-item>
              </div>
            </v-list-item-group>
            <hover-api-hint 
              v-if="api_hints_enabled" 
              :hover_api_hint.sync="hover_api_hint" 
              :lock_hover_api_hint.sync="lock_hover_api_hint" 
              :icons="icons"
            /> 
            <v-list-item class="dm-footer" v-if="loaded_n_data > 0">
              <v-list-item-content style="display: inline-block">
                <data-menu-remove
                  :delete_enabled="delete_enabled"
                  :delete_tooltip="delete_tooltip"
                  :delete_viewer_tooltip="delete_viewer_tooltip"
                  :delete_app_enabled="delete_app_enabled"
                  :delete_app_tooltip="delete_app_tooltip"
                  :api_hints_enabled="api_hints_enabled" 
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
                  :subset_edit_modes="subset_edit_modes"
                  :subset_tools="subset_tools"
                  :subset_selected="layer_selected[0]"
                  :api_hints_enabled="api_hints_enabled" 
                  @view-info="view_info"
                  @modify-subset="(combination_mode, tool) => {modify_subset({combination_mode: combination_mode,
                                                                              subset_type: tool});
                                                              data_menu_open = false}"
                />
              </v-list-item-content>
            </v-list-item>
          </v-list>
        </v-menu>
      </div>
      <div :id="'dm-target-' + viewer_id"></div> 
    </div>
    <div v-if="loaded_n_data == 0 && dataset_items.length > 0" style="height: 100%">
      <v-list style="height: 100%">
        <v-subheader><span>Load Data into Viewer</span></v-subheader>
        <v-list-item
          v-for="data in dataset_items"
        >
          <v-list-item-content>
            <j-tooltip tooltipcontent="add data to viewer">
              <span
                style="cursor: pointer; width: 100%"
                @click="add_data_to_viewer({data_label: data.label})"
              >
                {{ data.label }}
              </span>
            </j-tooltip>
          </v-list-item-content>
        </v-list-item>
      </v-list>
    </div>
  </div>
</template>

<script>
  module.exports = {
    data: function () {
      return {
        data_menu_open: false,
        hover_api_hint: '',
        lock_hover_api_hint: false
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
      this.jupyterLabCell = this.$el.closest(".jp-Notebook-cell");
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
    watch: {
      force_open_menu: function (val) {
        if (val) {
          this.data_menu_open = true;
          this.force_open_menu = false;
        }
      }
    },
    methods: {
      onScroll(e) {
        const dataMenuHeight = document.getElementById(`layer-legend-${this.viewer_id}`).parentElement.getBoundingClientRect().height
        const top = document.getElementById(`dm-target-${this.viewer_id}`).getBoundingClientRect().y + document.body.parentElement.scrollTop + dataMenuHeight;
        if (this.data_menu_open && document.getElementById(`dm-target-${this.viewer_id}`)) {
          const menuContent = document.getElementById(`dm-content-${this.viewer_id}`);
          menuContent.parentElement.style.top = top + "px";

          /* since Jupyter Lab 4.2 cells outside the view port get a height of 0, causing the menu to be visible when
           * that happens. This workaround hides the menu when it's parent cell is not in the viewport. */
          const labCellHidden = this.jupyterLabCell && window.getComputedStyle(this.jupyterLabCell).height === "0px";
          menuContent.parentElement.style.display = labCellHidden ? "none" : "";
        }
      },
      boolToString(b) {
        if (b) {
          return 'True'
        } else {
          return 'False'
        }
      }
    },
  }
</script>

<style scoped>
  .viewer-label-container {
    position: absolute;
    right: 0;
    z-index: 1;
    width: 24px;
  }
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
  .layer-select {
    /* spacing between entries so selections are more apparent */
    margin-top: 1px !important;
    margin-bottom: 1px !important;
  }
  .layer-select:nth-child(even) {
    /* alternating row colors */
    background-color: #f1f2f85a;
  }
  .active-list-item {
    background-color: #d1f4ff75 !important;
    font-weight: 500;
  }
  .dm-header, .dm-footer {
    background-color: #003B4D !important;
    font-weight: bold;
  }
  .dm-header > .v-list-item__icon, .dm-header > .v-list-item__content, .dm-header > .v-list-item__action,
  .dm-footer > .v-list-item__icon, .dm-footer > .v-list-item__content, .dm-footer > .v-list-item__action {
    filter: invert(1);
  }

  .dm-header.v-btn--disabled  .v-icon {
    color: green !important;
  }
  .pulse {
    animation: pulse_anim 2s infinite;
  }
  @keyframes pulse_anim {
    0% {
        transform: scale(0.95);
        box-shadow: 0 0 0 0 rgba(0, 0, 0, 0.7);
    }

    70% {
        transform: scale(1);
        box-shadow: 0 0 0 10px rgba(0, 0, 0, 0);
    }

    100% {
        transform: scale(0.95);
        box-shadow: 0 0 0 0 rgba(0, 0, 0, 0);
    }
}
</style>