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
        <j-tooltip :tooltipcontent="tooltipContent(item)">
          <v-btn
            :rounded="item.is_subset"
            @click="() => {if (!multiselect){$emit('update:selected', item.label)} else if(!selectedAsList.includes(item.label)) {$emit('update:selected', selected.concat(item.label))} else if (selected.length > 1) {$emit('update:selected', selected.filter(select => select != item.label))} }"
            :style="'padding: 0px; margin-bottom: 4px; background: '+visibilityStyle(item)+', '+colorStyle(item)"
            width="30px"
            min-width="30px"
            height="30px"
          >
            <span style="color: white; text-shadow: 0px 0px 3px black">
              {{ item.icon }}
            </span>
          </v-btn>
        </j-tooltip>
      </span>
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
  methods: {
    tooltipContent(item) {
      var tooltip = item.label
      if (item.visible === 'mixed') {
        tooltip += '<br/>Visibility: mixed'
      } else if (!item.visible) {
        tooltip += '<br/>Visibility: hidden'
      }
      if (this.$props.colormode === 'mixed' && !item.is_subset) {
        tooltip += '<br/>Color mode: mixed'
      }
      if (item.colors.length > 1) {
        if (this.$props.colormode === 'Colormaps') {
          tooltip += '<br/>Colormap: mixed'
        } else if (this.$props.colormode === 'mixed') {
          tooltip += '<br/>Color/colormap: mixed'
        } else {
          tooltip += '<br/>Color: mixed'
        }
      }
      return tooltip
    },
    visibilityStyle(item) {
      if (item.visible === 'mixed'){
        return 'repeating-linear-gradient(30deg, rgba(0,0,0,0.3), rgba(0,0,0,0.3) 3px, transparent 3px, transparent 3px, transparent 10px)'
      }
      else if (item.visible) {
        return 'repeating-linear-gradient(30deg, transparent, transparent 10px)'
      } else {
        return 'repeating-linear-gradient(30deg, rgba(0,0,0,0.4), rgba(0,0,0,0.4) 8px, transparent 8px, transparent 8px, transparent 10px)'
      }
    },
    colorStyle(item) {
      const strip_width = 42 / item.colors.length
      var cmap_strip_width = strip_width
      var colors = []
      var style = 'repeating-linear-gradient( 135deg, '
  
      for ([mi, color_or_cmap] of item.colors.entries()) {
        if (color_or_cmap.startsWith('#')) {
          colors = [color_or_cmap]
        } else {
          colors = this.$props.cmap_samples[color_or_cmap]
        }

        cmap_strip_width = strip_width / colors.length
        for ([ci, color] of colors.entries()) {
          var start = mi*strip_width + ci*cmap_strip_width
          var end = mi*strip_width+(ci+1)*cmap_strip_width
          style += color + ' '+start+'px, ' + color + ' '+end+'px'
          if (ci !== colors.length-1) {
            style += ', '
          }
        }
        if (mi !== item.colors.length-1) {
          style += ', '
        }
      }
    
      style += ')'
      return style

    }
  }
};
  
</script>
