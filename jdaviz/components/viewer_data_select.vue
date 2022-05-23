<template>
  <j-tooltip v-if="menuButtonAvailable()" tipid="viewer-toolbar-data">
    <v-menu offset-y :close-on-content-click="false" v-model="viewer.data_open">
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
  
      <v-list style="max-height: 500px; width: 350px; padding-top: 0px" class="overflow-y-auto">
        <v-row key="title" style="padding-left: 25px; margin-right: 0px; padding-bottom: 4px; background-color: #E3F2FD">
            <span class='text--primary' style="overflow-wrap: anywhere; font-size: 12pt; padding-top: 6px; padding-left: 6px; font-weight: bold">
              {{viewerTitleCase}}
            </span>

            <span style="position: absolute; right: 10px">
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

        <v-row v-for="item in filteredDataItems" :key="item.id" style="padding-left: 25px; margin-right: 0px">
          <j-viewer-data-select-item
            :item="item"
            :viewer="viewer"
            :multi_select="multi_select"
            @data-item-selected="$emit('data-item-selected', $event)"
            @data-item-remove="$emit('data-item-remove', $event)"
          ></j-viewer-data-select-item>
        </v-row>

        <div v-if="viewer.config === 'mosviz' && mosvizExtraDataItems.length" style="margin-bottom: -8px">
          <v-row key="mosviz-expand" style="padding-left: 25px; margin-right: 0px; padding-bottom: 4px; background-color: #E3F2FD"> 
            <span 
              @click="toggleMosvizShowExtraItems"
              class='text--primary' 
              style="overflow-wrap: anywhere; font-size: 12pt; padding-top: 6px; padding-left: 6px; cursor: pointer"
            >
              <v-icon>{{mosvizShowExtraItems ? 'mdi-chevron-double-up' : 'mdi-chevron-double-down'}}</v-icon>
              {{mosvizShowExtraItems ? 'hide from other MOS rows' : 'show from other MOS rows'}}
            </span>
          </v-row>

          <v-row v-if="mosvizShowExtraItems" v-for="item in mosvizExtraDataItems"  :key="item.id" style="padding-left: 25px; margin-right: 0px">
            <j-viewer-data-select-item
              :item="item"
              :viewer="viewer"
              :multi_select="multi_select"
              @data-item-selected="$emit('data-item-selected', $event)"
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
  props: ['data_items', 'viewer', 'app_settings', 'icons'],
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
    }
    return {
      // default to passed values, whenever value or uncertainty are changed
      // updateTruncatedValues will overwrite the displayed values
      multi_select: multi_select,
      mosvizShowExtraItems: false,
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
    itemIsVisible(item, mosvizExtraItems) {
      if (this.$props.viewer.config === 'mosviz') {
        if (this.$props.viewer.reference === 'spectrum-viewer' && item.type !== '1d spectrum') {
          // filters out table, spectrum 2d, images
          return false
        } else if (this.$props.viewer.reference === 'spectrum-2d-viewer' && item.type !== '2d spectrum') {
          return false
        } else if (this.$props.viewer.reference === 'image-viewer' && item.type !== 'image') {
          return false
        } else if (item.meta.mosviz_row !== undefined) {
          if (mosvizExtraItems) {
            // then show only plugin items and only those in a different row
            return item.meta.mosviz_row !== this.$props.app_settings.mosviz_row
          } else {
            // show ONLY items from the SAME row
            return item.meta.mosviz_row == this.$props.app_settings.mosviz_row
          }
        }
        return !mosvizExtraItems
      } else if (this.$props.viewer.config === 'cubeviz') {
        if (this.$props.viewer.reference === 'spectrum-viewer') {
          if (item.meta.Plugin === undefined) {
            // then the data can be a cube (auto-collapsed) as long as its the flux data
            return item.name.indexOf('[FLUX]') !== -1
          } else if (item.meta.Plugin === 'GaussianSmooth') {
            // spectrally smoothed would still be a collapsible cube
            return item.ndims === 3
          } else {
            // filter plugin results to only those that are spectra
            return item.ndims === 1
          }
        } else {
          // then we're one of the three image viewers
          // filter out non-images (support 2d images and cubes)
          return item.ndims >= 2
        }
      } else if (this.$props.viewer.config === 'specviz2d') {
        if (this.$props.viewer.reference === 'spectrum-viewer') {
          return item.ndims === 1
        } else if (this.$props.viewer.reference === 'spectrum-2d-viewer') {
          return item.ndims === 2
        }
      }
      // for any situation not covered above, default to showing the entry
      return true
    },
    toggleMosvizShowExtraItems() {
      if (this.mosvizShowExtraItems) {
        // uncheck all checked items
        this.mosvizExtraDataItems.forEach((item) => {
          if (this.$props.viewer.selected_data_items.includes(item.id)) {
            this.$emit('data-item-selected', {
              id: this.$props.viewer.id,
              item_id: item.id,
              checked: false,
              replace: false})
          }
        })
      }
      // toggle the visibility of the extra items in the menu
      this.mosvizShowExtraItems = !this.mosvizShowExtraItems
    },
  },
  computed: {
    viewerTitleCase() {
      var title = this.$props.viewer.reference || this.$props.viewer.id
      return title.toLowerCase().replaceAll('-', ' ').split(' ').map((word) => {return (word.charAt(0).toUpperCase() + word.slice(1))}).join(' ');
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
    mosvizExtraDataItems() {
      return this.$props.data_items.filter((item) => this.itemIsVisible(item, true))
    },
  }
};
</script>
