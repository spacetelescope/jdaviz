<template>
  <j-tooltip v-if="menuButtonAvailable()" tipid="viewer-toolbar-data">
    <v-menu offset-y :close-on-content-click="false" v-model="data_menu_open">
      <template v-slot:activator="{ on, attrs }">
        <v-btn
          :id="'menu-button-'+ viewer.id"
          text 
          elevation="3" 
          v-bind="attrs" 
          v-on="on" 
          color="white"
          tile
          icon
          outlined
          :class="{active: data_menu_open}"
          style="height: 42px; width: 42px">
          <v-icon>mdi-format-list-bulleted-square</v-icon>
        </v-btn>
      </template>
      <v-list :id="'menu-content-' + viewer.id" style="max-height: 500px; width: 465px; padding-top: 0px" class="overflow-y-auto">
        <v-row key="title" style="padding-left: 25px; margin-right: 0px; background-color: #E3F2FD">
            <span style="overflow-wrap: anywhere; font-size: 12pt; padding-top: 6px; padding-left: 6px; font-weight: bold; color: black">
              {{viewerTitleCase}}
            </span>

            <span style="position: absolute; right: 5px">
              <j-tooltip :tipid="multi_select ? 'viewer-data-select-enabled' : 'viewer-data-radio-enabled'">
                <v-btn
                  icon
                  @click="toggleMultiSelect"
                  style="opacity: 0.7"
                  >
                    <img :src="multi_select ? icons.checktoradial : icons.radialtocheck" width="24"/>
                </v-btn>
              </j-tooltip>
            </span>
        </v-row>

        <v-row style="padding-left: 32px; margin-right: 0px; padding-right: 10px;
                      padding-bottom: 6px; background-color: #E3F2FD;
                      color: black">
          <span>
            Add more datasets using the "Import Data" button or via the API.
          </span>
        </v-row>

        <v-row v-for="item in filteredDataItems" :key="item.id" style="padding-left: 25px; margin-right: 0px; margin-top: 4px; margin-bottom: 4px">
          <j-viewer-data-select-item
            :item="item"
            :icon="layer_icons[item.name]"
            :icons="icons"
            :viewer="viewer"
            :multi_select="multi_select"
            :is_wcs_only="false"
            :n_data_entries="nDataEntries"
            @data-item-visibility="$emit('data-item-visibility', $event)"
            @data-item-unload="$emit('data-item-unload', $event)"
            @data-item-remove="$emit('data-item-remove', $event)"
          ></j-viewer-data-select-item>
        </v-row>

        <div v-if="linkedByWcs()">
          <j-plugin-section-header style="margin-top: 0px">Orientation</j-plugin-section-header>
          <v-row v-for="item in wcsOnlyItems" :key="item.id" style="padding-left: 25px; margin-right: -8px; margin-top: 4px; margin-bottom: 4px">
            <j-viewer-data-select-item
              :item="item"
              :icon="layer_icons[item.name]"
              :icons="icons"
              :viewer="viewer"
              :multi_select="multi_select"
              :is_wcs_only="true"
              @data-item-remove="$emit('data-item-remove', $event)"
              @change-reference-data="$emit('change-reference-data', $event)"
            ></j-viewer-data-select-item>
          </v-row>
        </div>

        <div v-if="extraDataItems.length > 0" style="margin-bottom: -8px;">
          <v-row key="extra-items-expand" style="padding-left: 25px; margin-right: 0px; padding-bottom: 4px; background-color: #E3F2FD"> 
            <span 
              @click="toggleShowExtraItems"
              class='text--primary'
              style="overflow-wrap: anywhere; font-size: 12pt; padding-top: 6px; padding-left: 6px; cursor: pointer"
            >
              <v-icon class='invert-if-dark'>{{showExtraItems ? 'mdi-chevron-double-up' : 'mdi-chevron-double-down'}}</v-icon>
              <span v-if="viewer.config === 'mosviz'">
                {{showExtraItems ? 'hide other row data not in viewer' : 'show other row data not in viewer'}}
              </span>
              <span v-else>
                {{showExtraItems ? 'hide data not in viewer' : 'show data not in viewer'}}
              </span>
            </span>
          </v-row>

          <v-row v-if="showExtraItems" v-for="item in extraDataItems" :key="item.id" style="padding-left: 25px; margin-right: 0px; margin-top: 4px; margin-bottom: 4px">
            <j-viewer-data-select-item
              :item="item"
              :icon="layer_icons[item.name]"
              :icons="icons"
              :viewer="viewer"
              :multi_select="multi_select"
              :is_wcs_only="false"
              :n_data_entries="nDataEntries"
              @data-item-visibility="$emit('data-item-visibility', $event)"
              @data-item-remove="$emit('data-item-remove', $event)"
            ></j-viewer-data-select-item>
          </v-row>
        </div>
      </v-list>
    </v-menu>
    <div :id="'target-' + viewer.id"></div>
  </j-tooltip>
</template>
<script>

module.exports = {
  props: ['data_items', 'viewer', 'layer_icons', 'app_settings', 'icons'],
  data: function () {
    var multi_select = true
    if (this.$props.viewer.config === 'cubeviz') {
      if (this.$props.viewer.reference !== 'spectrum-viewer') {
        multi_select = false
      }
    } else if (this.$props.viewer.config === 'mosviz') {
      if (['image-viewer', 'spectrum-2d-viewer'].indexOf(this.$props.viewer.reference) !== -1) {
        multi_select = false
      }
    } else if (this.$props.viewer.config === 'specviz2d') {
      if (this.$props.viewer.reference === 'spectrum-2d-viewer') {
        multi_select = false
      }
    } else if (this.$props.viewer.config === 'lcviz') {
      if (this.$props.viewer.reference.startsWith('image')) {
        multi_select = false
      }
    }
    return {
      // default to passed values, whenever value or uncertainty are changed
      // updateTruncatedValues will overwrite the displayed values
      data_menu_open: this.$props.viewer.open_data_menu_if_empty && Object.keys(this.$props.viewer.selected_data_items).length == 0 && this.$props.data_items.length > 0,
      multi_select: multi_select,
      showExtraItems: Object.keys(this.$props.viewer.selected_data_items).length == 0,
      valueTrunc: this.value,
      uncertTrunc: this.uncertainty,
    }
  },
  mounted() {
    let element = document.getElementById(`target-${this.viewer.id}`).parentElement
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
    let element = document.getElementById(`target-${this.viewer.id}`).parentElement
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
      const dataMenuHeight = document.getElementById(`menu-button-${this.viewer.id}`).parentElement.getBoundingClientRect().height
      const top = document.getElementById(`target-${this.viewer.id}`).getBoundingClientRect().y + document.body.parentElement.scrollTop + dataMenuHeight;
      if (this.data_menu_open && document.getElementById(`target-${this.viewer.id}`)) {
        const menuContent = document.getElementById(`menu-content-${this.viewer.id}`);
        menuContent.parentElement.style.top = top + "px";
      }
    },
    menuButtonAvailable() {
      if (this.$props.viewer.reference === 'table-viewer') {
        return false
      }
      return true
    },
    dataItemInViewer(item, returnExtraItems) {
      const inViewer = Object.keys(this.$props.viewer.selected_data_items).includes(item.id)
      if (returnExtraItems) {
        return (!inViewer && (item.meta.mosviz_row === this.$props.app_settings.mosviz_row))
      }
      return inViewer
    },
    wcsOnlyItem(item) {
      return item.type == 'wcs-only'
    },
    itemIsVisible(item, returnExtraItems) {
      if (this.$props.viewer.config === 'mosviz') {
        if (this.$props.viewer.reference === 'spectrum-viewer' && item.type !== '1d spectrum') {
          // filters out table, spectrum 2d, images
          return false
        } else if (this.$props.viewer.reference === 'spectrum-2d-viewer' && item.type !== '2d spectrum') {
          return false
        } else if (this.$props.viewer.reference === 'image-viewer' && item.type !== 'image') {
          return false
        } else {
          return this.dataItemInViewer(item, returnExtraItems)
        }
      } else if (this.$props.viewer.config === 'cubeviz') {
        if (this.$props.viewer.reference === 'spectrum-viewer') {
          if (item.meta.Plugin === undefined) {
            // then the data can be a cube (auto-collapsed) as long as its the flux data
            // if this logic moves to python, we could check directly against reference data instead
            return (item.name.indexOf('[FLUX]') !== -1 || item.name.indexOf('[SCI]') !== -1) && this.dataItemInViewer(item, returnExtraItems)
          } else if (item.meta.Plugin === 'GaussianSmooth') {
            // spectrally smoothed would still be a collapsible cube
            return item.ndims === 3 && this.dataItemInViewer(item, returnExtraItems)
          } else {
            // filter plugin results to only those that are spectra
            return item.ndims === 1 && this.dataItemInViewer(item, returnExtraItems)
          }
        } else {
          // then we're one of the three image viewers
          // filter out non-images (support 2d images and cubes)
          return item.ndims >= 2 && this.dataItemInViewer(item, returnExtraItems)
        }
      } else if (this.$props.viewer.config === 'specviz2d') {
        if (this.$props.viewer.reference === 'spectrum-viewer') {
          return item.ndims === 1 && item.type!=='trace' && this.dataItemInViewer(item, returnExtraItems)
        } else if (this.$props.viewer.reference === 'spectrum-2d-viewer') {
          return (item.ndims === 2 || item.type==='trace') && this.dataItemInViewer(item, returnExtraItems)
        }
      } else if (this.$props.viewer.config === 'lcviz') {
        // TODO: generalize itemIsVisible so downstream apps can provide their own customized filters
        if (this.$props.viewer.reference.startsWith('image')) {
          return (item.ndims === 3 && this.dataItemInViewer(item, returnExtraItems))
        }
        if (item.meta._LCVIZ_EPHEMERIS !== undefined) {
          if (!this.$props.viewer.reference.startsWith('flux-vs-phase:')) {
            return false
          }
          var viewer_ephem_comp = this.$props.viewer.reference.split('flux-vs-phase:')[1].split('[')[0]
          return item.ndims === 1 && item.meta._LCVIZ_EPHEMERIS.ephemeris == viewer_ephem_comp && this.dataItemInViewer(item, returnExtraItems)
        }
        return item.ndims === 1 && this.dataItemInViewer(item, returnExtraItems)
      } else if (this.$props.viewer.config === 'imviz') {
        return this.dataItemInViewer(item, returnExtraItems && !this.wcsOnlyItem(item))
      }
      // for any situation not covered above, default to showing the entry
      return this.dataItemInViewer(item, returnExtraItems)
    },
    toggleShowExtraItems() {
      // toggle the visibility of the extra items in the menu
      this.showExtraItems = !this.showExtraItems
    },
    toggleMultiSelect() {
      this.multi_select = !this.multi_select
      if (this.multi_select === false) {
        // If we're toggling to single select, set the first item visibility to replace the rest
        // Find the "first" item
        for (item_index in this.filteredDataItems) {
          if (this.$props.viewer.selected_data_items[this.filteredDataItems[item_index].id] === 'visible') {
            this.$emit('data-item-visibility', {
              id: this.$props.viewer.id,
              item_id: this.filteredDataItems[item_index].id,
              visible: true,
              replace: true
            })
            break;
          }
        }
      }
    },
    isRefData() {
      return this.$props.item.viewer.reference_data_label === this.$props.item.name
    },
    selectRefData() {
      this.$emit('change-reference-data', {
        id: this.$props.viewer.id,
        item_id: this.$props.item.id
      })
    },
    linkedByWcs() {
      return this.$props.viewer.linked_by_wcs
    }
  },
  computed: {
    viewerTitleCase() {
      var title = this.$props.viewer.reference || this.$props.viewer.id
      // this translates from kebab-case to human readable (individual words, in title case)
      // each word that should NOT be capitalized needs to explicitly be set here
      return title.toLowerCase().replaceAll('-', ' ').split(' ').map((word) => {if (['vs'].indexOf(word) !== -1) {return word} else {return word.charAt(0).toUpperCase() + word.slice(1)}}).join(' ');
    },
    showModeToggle() {
      if (this.$props.viewer.config === 'cubeviz') {
        if (this.$props.viewer.reference !== 'spectrum-viewer') {
          return true
        }
      }
      return false
    },
    filteredDataItems() {
      return this.$props.data_items.filter((item) => this.itemIsVisible(item, false))
    },
    extraDataItems() {
      return this.$props.data_items.filter((item) => this.itemIsVisible(item, true))
    },
    nDataEntries() {
      // return number of data entries in the entire plugin that were NOT created by a plugin
      return this.$props.data_items.filter((item) => item.meta.Plugin === undefined).length
    },
    wcsOnlyItems() {
      return this.$props.data_items.filter((item) => this.wcsOnlyItem(item))
    },
  }
};
</script>
