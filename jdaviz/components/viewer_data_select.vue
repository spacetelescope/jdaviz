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
  
      <v-list style="max-height: 500px; width: 350px;" class="overflow-y-auto">
        <v-row v-for="item in filteredDataItems" :key="item.id" style="padding-left: 25px">
          <j-tooltip tipid='viewer-data-select-toggle'>
            <v-btn 
              icon
              :color="viewer.selected_data_items.includes(item.id) ? 'accent' : 'default'"
              @click="$emit('data-item-selected', {
                id: viewer.id,
                item_id: item.id,
                checked: !viewer.selected_data_items.includes(item.id)
              })">
                <v-icon>{{viewer.selected_data_items.includes(item.id) ? "mdi-eye" : "mdi-eye-off"}}</v-icon>
            </v-btn>
          </j-tooltip>

          <span class='text--primary' style="overflow-wrap: anywhere; font-size: 12pt; padding-top: 6px; padding-left: 6px">
            {{item.name}}
          </span>

          <div style="position: absolute; right: 10px">
            <j-tooltip tipid='viewer-data-select-delete'>
              <v-btn
                icon
                @click="$emit('data-item-remove', {item_name: item.name})"
              ><v-icon>mdi-delete</v-icon></v-btn>
            </j-tooltip>
          </div>
        </v-row>
      </v-list>

    </v-menu>
  </j-tooltip>
</template>
<script>

module.exports = {
  props: ['data_items', 'viewer'],
  methods: {
    menuButtonAvailable() {
      if (this.$props.viewer.config === 'mosviz') {
        if (this.$props.viewer.reference !== 'spectrum-viewer') {
          // if making available for other viewers, those cases will also
          // need to be handled in filteredDataItems below.
          return false
        }
      }
      return true
    },
  },
  computed: {
    filteredDataItems() {
      itemIsVisible = (item) => {
        if (this.$props.viewer.config === 'mosviz') {
          if (this.$props.viewer.reference === 'spectrum-viewer') {
            if (item.ndims !== 1) {
              // filters out table, spectrum 2d, images
              return false
            } else if (item.meta.Plugin === undefined) {
              console.log("***", item.name, item.meta.mosviz_row)
            }
            return true
          }
        } else if (this.$props.viewer.config === 'cubeviz') {
          if (this.$props.viewer.reference === 'spectrum-viewer') {
            if (item.meta.Plugin === undefined) {
              // then the data can be a cube (auto-collapsed) as long as its the flux data
              return item.name.indexOf('[FLUX]') !== -1
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
      }

      return this.$props.data_items.filter(itemIsVisible)
    }
  }
};
</script>
