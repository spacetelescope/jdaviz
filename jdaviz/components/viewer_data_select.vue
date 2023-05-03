<template>
  <j-tooltip v-if="menuButtonAvailable()" tipid="viewer-toolbar-data">
    <v-menu attach offset-y :close-on-content-click="false" v-model="viewer.data_open">
      <template v-slot:activator="{ on, attrs }">
        <v-btn 
          text 
          elevation="3" 
          v-bind="attrs" 
          v-on="on" 
          color="white"
          tile
          icon
          outlined
          :class="{active: viewer.data_open}"
          style="height: 42px; width: 42px">
          <v-icon>mdi-format-list-bulleted-square</v-icon>
        </v-btn>
      </template>
  
      <v-list style="max-height: 500px; width: 460px; padding-top: 0px" class="overflow-y-auto">
        <v-row key="title" style="padding-left: 25px; margin-right: 0px; background-color: #E3F2FD">
            <span style="overflow-wrap: anywhere; font-size: 12pt; padding-top: 6px; padding-left: 6px; font-weight: bold; color: black">
              {{viewerTitleCase}}
            </span>

            <span style="position: absolute; right: 5px">
              <j-tooltip :tipid="multi_select ? 'viewer-data-select-enabled' : 'viewer-data-radio-enabled'">
                <v-btn
                  icon
                  @click="() => {multi_select = !multi_select}"
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
            :viewer="viewer"
            :multi_select="multi_select"
            @data-item-visibility="$emit('data-item-visibility', $event)"
            @data-item-unload="$emit('data-item-unload', $event)"
            @data-item-remove="$emit('data-item-remove', $event)"
          ></j-viewer-data-select-item>
        </v-row>

        <div v-if="extraDataItems.length" style="margin-bottom: -8px;">
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

          <v-row v-if="showExtraItems" v-for="item in extraDataItems"  :key="item.id" style="padding-left: 25px; margin-right: 0px; margin-top: 4px; margin-bottom: 4px">
            <j-viewer-data-select-item
              :item="item"
              :icon="layer_icons[item.name]"
              :viewer="viewer"
              :multi_select="multi_select"
              @data-item-visibility="$emit('data-item-visibility', $event)"
              @data-item-remove="$emit('data-item-remove', $event)"
            ></j-viewer-data-select-item>
          </v-row>
        </div>

      </v-list>

    </v-menu>
  </j-tooltip>
</template>
<script>

module.exports = {
  props: ['data_items', 'viewer', 'layer_icons', 'app_settings', 'viewer_data_visibility', 'icons'],
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
    }
    return {
      // default to passed values, whenever value or uncertainty are changed
      // updateTruncatedValues will overwrite the displayed values
      multi_select: multi_select,
      showExtraItems: false,
      valueTrunc: this.value,
      uncertTrunc: this.uncertainty
    }
  },
  methods: {
    menuButtonAvailable() {
      if (this.$props.viewer.reference === 'table-viewer') {
        return false
      }
      return true
    },
    dataItemInViewer(item, returnExtraItems) {
      const inViewer = Object.keys(this.$props.viewer.selected_data_items).includes(item.id)
      //console.log(item.name+"  "+inViewer)
      if (returnExtraItems) {
        return (!inViewer && (item.meta.mosviz_row === this.$props.app_settings.mosviz_row))
      }
      return inViewer
    },
    wcsOnlyItemInViewer(item) {
      const wcsOnly = Object.keys(this.$props.viewer.wcs_only_layers).includes(item.name)
      return wcsOnly
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
            return item.name.indexOf('[FLUX]') !== -1 && this.dataItemInViewer(item, returnExtraItems)
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
      } else if (this.$props.viewer.config === 'imviz') {
        return this.dataItemInViewer(item, returnExtraItems) && !this.wcsOnlyItemInViewer(item)
      }
      // for any situation not covered above, default to showing the entry
      return this.dataItemInViewer(item, returnExtraItems)
    },
    toggleShowExtraItems() {
      // toggle the visibility of the extra items in the menu
      this.showExtraItems = !this.showExtraItems
    },
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
  }
};
</script>
