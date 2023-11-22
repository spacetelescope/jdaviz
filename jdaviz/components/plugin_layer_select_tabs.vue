<template>
  <div>
    <span class="suppress-scrollbar" style="display: inline-block; white-space: nowrap; margin-left: -24px; width: calc(100% + 48px); overflow-x: scroll; overflow-y: hidden">
      <span v-for="(item, index) in items" :class="selectedAsList.includes(item.label) ? 'layer-tab-selected' : ''" :style="'display: inline-block; padding: 12px; '+(selectedAsList.includes(item.label) ? 'border-top: 3px solid #00617E' : 'border-top: 3px solid transparent')">
        <j-tooltip :tooltipcontent="tooltipContent(item)">
          <v-btn
            :rounded="item.is_subset"
            @click="() => {if (!multiselect){$emit('update:selected', item.label)} else if(!selectedAsList.includes(item.label)) {$emit('update:selected', selected.concat(item.label))} else {$emit('update:selected', selected.filter(select => select != item.label))} }"
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
  props: ['items', 'selected', 'multiselect', 'colormode', 'cmap_samples'],
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
      if (item.mixed_visibility) {
        tooltip += '<br/>Visibility: mixed'
      } else if (!item.visible) {
        tooltip += '<br/>Visibility: hidden'
      }
      if (this.$props.colormode === 'mixed' && !item.is_subset) {
        tooltip += '<br/>Color mode: mixed'
      }
      if (item.mixed_color && (this.$props.colormode !== 'Colormaps' || item.is_subset)) {
        tooltip += '<br/>Color: mixed'
      }
      return tooltip
    },
    visibilityStyle(item) {
      if (item.mixed_visibility){
        return 'repeating-linear-gradient(30deg, rgba(0,0,0,0.3), rgba(0,0,0,0.3) 3px, transparent 3px, transparent 3px, transparent 10px)'
      }
      else if (item.visible) {
        return 'repeating-linear-gradient(30deg, transparent, transparent 10px)'
      } else {
        return 'repeating-linear-gradient(30deg, rgba(0,0,0,0.4), rgba(0,0,0,0.4) 8px, transparent 8px, transparent 8px, transparent 10px)'
      }
    },
    colorStyle(item) {
      const strip_width = 42 / item.color.length

      var style = 'repeating-linear-gradient( 135deg, '
      if (this.$props.colormode !== 'Colormaps' || item.is_subset) {
        for ([ind, color] of item.color.entries()) {
          style += color + ' '+ind*strip_width+'px, ' + color + ' '+(ind+1)*strip_width+'px'
          if (ind !== item.color.length-1) {
            style += ', '
          }
        }
      } else {
        // colormaps
        for ([mi, cmap] of item.cmap.entries()) {
          var colors = this.$props.cmap_samples[cmap]
          var cmap_strip_width = strip_width / colors.length
          for ([ci, color] of colors.entries()) {
            var start = mi*strip_width + ci*cmap_strip_width
            var end = mi*strip_width+(ci+1)*cmap_strip_width
            style += color + ' '+start+'px, ' + color + ' '+end+'px'
            if (ci !== colors.length-1) {
              style += ', '
            }
          }
          if (mi !== item.cmap.length-1) {
            style += ', '
          }
        }
      }
      style += ')'
      return style

    }
  }
};
  
</script>

<style scoped>
  .suppress-scrollbar {
      overflow-y: scroll;
      scrollbar-width: none; /* Firefox */
      -ms-overflow-style: none;  /* Internet Explorer 10+ */
  }
  .suppress-scrollbar::-webkit-scrollbar { /* WebKit */
      width: 0;
      height: 0;
  }
</style>
