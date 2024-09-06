<template>
  <div style="margin-top: 24px">
    <div v-if="show_multiselect_toggle" style="position: absolute; width: 32px; right: 0px; margin-right: 12px; margin-top: -32px">
      <j-tooltip tipid='layer-multiselect-toggle'>
        <v-btn
          icon
          style="opacity: 0.7"
          @click="$emit('update:multiselect', !multiselect)"
        >
          <img :src="multiselect ? icon_checktoradial : icon_radialtocheck" width="24" class="invert-if-dark"/>
        </v-btn>
      </j-tooltip>
    </div>
    <span style="display: inline-block; white-space: nowrap; margin-left: -24px; width: calc(100% + 48px); overflow-x: scroll; overflow-y: hidden">
      <span v-for="(item, index) in items" :class="selectedAsList.includes(item.label) ? 'layer-tab-selected' : ''" :style="'display: inline-block; padding: 8px; '+(selectedAsList.includes(item.label) ? 'border-top: 3px solid #00617E' : 'border-top: 3px solid transparent')">
        <j-layer-viewer-icon-stylized
          :label="item.label"
          :icon="item.icon"
          :visible="item.visible"
          :is_subset="item.is_subset"
          :colors="item.colors"
          :linewidth="item.linewidth"
          :colormode="colormode"
          :cmap_samples="cmap_samples"
          @click="() => {if (!multiselect){$emit('update:selected', item.label)} else if(!selectedAsList.includes(item.label)) {$emit('update:selected', selected.concat(item.label))} else if (selected.length > 1) {$emit('update:selected', selected.filter(select => select != item.label))} }"
        />
    </span>
 </div>
</template>

<script>
module.exports = {
  props: ['items', 'selected', 'multiselect', 'colormode', 'cmap_samples',
          'show_multiselect_toggle', 'icon_checktoradial', 'icon_radialtocheck'],
  computed: {
    selectedAsList() {
      if (this.$props.multiselect) { 
        return this.$props.selected
      }
      return [this.$props.selected]
    }
  },
};
  
</script>
