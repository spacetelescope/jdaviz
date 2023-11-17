<template>
  <div>
    <span class="suppress-scrollbar" style="display: inline-block; white-space: nowrap; margin-left: -24px; width: calc(100% + 48px); overflow-x: scroll; overflow-y: hidden">
      <span v-for="(item, index) in items" :class="selected.includes(item.label) ? 'layer-tab-selected' : ''" :style="'display: inline-block; padding: 12px; '+(selected.includes(item.label) ? 'border-top: 2px solid #c75109' : 'border-top: 2px solid transparent')">
        <j-tooltip :tooltipcontent="tooltipContent(item)">
          <v-btn
            :rounded="item.is_subset"
            @click="() => {if (!multiselect){$emit('update:selected', item.label)} else if(selected.indexOf(item.label) === -1) {$emit('update:selected', selected.concat(item.label))} else {$emit('update:selected', selected.filter(select => select != item.label))} }"
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
  props: ['items', 'selected', 'multiselect', 'colormode'],
  methods: {
    tooltipContent(item) {
      var tooltip = item.label
      if (item.mixed_visibility) {
        tooltip += '<br/>Visible: mixed'
      } else if (!item.visible) {
        tooltip += '<br/>Visible: false'
      }
      if (this.$props.colormode === 'Colormaps' && !item.is_subset) {
        tooltip += '<br/>Color mode: colormap'
      } else if (this.$props.colormode === 'mixed' && !item.is_subset) {
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
        return 'repeating-linear-gradient(30deg, rgba(0,0,0,0.8), rgba(0,0,0,0.8) 7px, transparent 7px, transparent 7px, transparent 10px)'
      }
    },
    colorStyle(item) {
      if (this.$props.colormode == 'Colormaps' && !item.is_subset) {
        return 'repeating-linear-gradient( -45deg, gray, gray 20px)'
      }
      if (item.mixed_color) {
        colors = item.all_colors_to_label
        const strip_width = 42 / colors.length

        var style = 'repeating-linear-gradient( -45deg, '
        for ([ind, color] of colors.entries()) {
          style += color + ' '+ind*strip_width+'px, ' + color + ' '+(ind+1)*strip_width+'px'
          if (ind !== colors.length-1) {
            style += ', '
          }
        }
        style += ')'
        return style
      } 
      return 'repeating-linear-gradient( -45deg, '+item.color+', '+item.color+' 20px)'

    }
  }
};
  
</script>
