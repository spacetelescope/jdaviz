<template>
  <div style="display: contents">
    <div v-if="isSelected">
      <j-tooltip :tipid="multi_select ? 'viewer-data-select' : 'viewer-data-radio'">
        <v-btn 
          icon
          :color="visibleState==='visible' ? 'accent' : 'default'"
          @click="selectClicked">
            <v-icon v-if="multi_select || item.type==='trace'">{{visibleState!=='hidden' ? "mdi-checkbox-marked" : "mdi-checkbox-blank-outline"}}</v-icon>
            <v-icon v-else>{{visibleState!=='hidden' ? "mdi-radiobox-marked" : "mdi-radiobox-blank"}}</v-icon>
        </v-btn>
      </j-tooltip>
    </div>
    <div v-else>
      <j-tooltip tipid="viewer-data-enable">
        <v-btn v-if="this.$props.item.type !== 'wcs-only'"
          icon
          color="default"
          @click="selectClicked">
            <v-icon>mdi-plus</v-icon>
        </v-btn>
      </j-tooltip>
    </div>

    <j-tooltip :tooltipcontent="'data label: '+item.name" span_style="font-size: 12pt; padding-top: 6px; padding-left: 6px; width: calc(100% - 80px); white-space: nowrap; cursor: default;">
      <j-layer-viewer-icon span_style="margin-left: 4px; margin-right: 2px" :icon="icon" color="#000000DE"></j-layer-viewer-icon>      
      <div class="text-ellipsis-middle" style="font-weight: 500">
        <span>
          {{itemNamePrefix}}
        </span>
        <span>
          {{itemNameExtension}}
        </span>
      </div>
    </j-tooltip>

    <div v-if="isSelected && isUnloadable" style="right: 2px">
      <j-tooltip tipid='viewer-data-disable'>
        <v-btn
          icon
          @click="$emit('data-item-unload', {
            id: viewer.id,
            item_id: item.id
          })"
        ><v-icon>mdi-close</v-icon></v-btn>
      </j-tooltip>
    </div>

    <div v-if="isDeletable" style="right: 2px">
      <j-tooltip tipid='viewer-data-delete'>
        <v-btn
          icon
          @click="$emit('data-item-remove', {item_name: item.name})"
        ><v-icon>mdi-delete</v-icon></v-btn>
      </j-tooltip>
    </div>
  </div>
</template>

<script>

module.exports = {
  props: ['item', 'icon', 'multi_select', 'viewer'],
  methods: {
    selectClicked() {
      prevVisibleState = this.visibleState
      // checkboxes control VISIBILITY of layers not loaded state
      // if we just loaded the data, its probably already visible, but we'll still make sure all
      // appropriate layers are visible and properly handle replace for non-multiselect
      // NOTE: replace=True will exclude removing trace items
      this.$emit('data-item-visibility', {
        id: this.$props.viewer.id,
        item_id: this.$props.item.id,
        visible: prevVisibleState != 'visible' || (!this.multi_select && this.$props.item.type !== 'trace'),
        replace: !this.multi_select && this.$props.item.type !== 'trace'
      })
    }
  },
  computed: {
    itemNamePrefix() {
      if (this.$props.item.name.indexOf("[") !== -1) {
        // return everything BEFORE the LAST [
        return this.$props.item.name.split('[').slice(0, -1).join()
      } else {
        return this.$props.item.name
      }
    },
    itemNameExtension() {
      if (this.$props.item.name.indexOf("[") !== -1) {
        // return the LAST [ and everything FOLLOWING
        return '['+this.$props.item.name.split('[').slice(-1)
      } else {
        return ''
      }
    },
    isSelected() {
      return Object.keys(this.$props.viewer.selected_data_items).includes(this.$props.item.id)
    },
    visibleState() {
      return this.$props.viewer.selected_data_items[this.$props.item.id] || 'hidden'
    },
    isUnloadable() {
      if (this.$props.item.meta.Plugin !== undefined) {
        // (almost) always allow unloading plugin exports
        if (this.$props.viewer.config === 'specviz2d' && this.$props.item.name === 'Spectrum 1D') {
          // the "Spectrum 1D" object is auto-generated from a plugin, but since its the default
          // reference data, we don't want to allow unloading it
          return false
        }
        return true
      }
      if (this.$props.viewer.config === 'cubeviz') {
        // forbid unloading the original reference cube
        // this logic might need to be generalized if supporting custom data labels
        // per-cube or renaming data labels
        if (this.$props.viewer.reference === 'flux-viewer') {
          return this.$props.item.name.indexOf('[FLUX]') === -1
        } else if (this.$props.viewer.reference === 'uncert-viewer') {
          return this.$props.item.name.indexOf('[IVAR]') === -1
        } else if (this.$props.viewer.reference === 'mask-viewer') {
          return this.$props.item.name.indexOf('[MASK]') === -1
        } else if (this.$props.viewer.reference === 'spectrum-viewer') {
          return this.$props.item.name.indexOf('[FLUX]') === -1          
        }
      } else if (this.$props.viewer.config === 'specviz2d') {
        if (this.$props.viewer.reference === 'spectrum-2d-viewer') {
          return this.$props.item.name !== 'Spectrum 2D'
        } else if (this.$props.viewer.reference === 'spectrum-viewer') {
          return this.$props.item.name !== 'Spectrum 1D'
        }
      }
      return true
    },
    isDeletable() {
      // only allow deleting products from plugins.  We might want to allow some non-plugin
      // data to also be deleted in the future, but would probably need more advanced logic
      // to ensure essential data isn't removed that would break the app.
      if (this.$props.item.meta.Plugin === undefined) {
        return false
      }
      // for any exceptions not above, enable deleting
      return !this.isSelected
    },
    selectTipId() {
      if (this.multi_select) {
        return 'viewer-data-select'
      } else {
        return 'viewer-data-radio'
      }
    },
    labelColor() {
      if (this.isSelected) {
        return 'black'
      } else {
        return 'gray'
      }
    }
  }
};
</script>

<style>
  .text-ellipsis-middle {
    display: inline-flex;
    flex-wrap: nowrap;
    max-width: 100%;
  }

  .text-ellipsis-middle > span:first-child {
    flex: 0 1 auto;
    text-overflow: ellipsis;
    overflow:hidden;
    white-space:nowrap;
  }

  .text-ellipsis-middle > span + span {
    flex: 1 0 auto;
    white-space: nowrap;
  }
</style>
