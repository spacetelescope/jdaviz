<template>
  <div>
    <span style="display: inline-block; white-space: nowrap; margin-left: -24px; width: calc(100% + 48px); overflow-x: scroll; overflow-y: hidden">
      <span v-for="(item, index) in items" :style="'display: inline-block; padding: 12px; '+(selected.includes(item.label) ? 'background-color: rgba(0,0,0,0.1)' : '')">
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
      if (!item.visible) {
        tooltip += '<br/>Visible: false'
      }
      if (this.$props.colormode === 'Colormaps') {
        tooltip += '<br/>Color mode: colormap'
      } else if (this.$props.colormode === 'mixed') {
        tooltip += '<br/>Color mode: mixed'
      }
      if (item.mixed_color && this.$props.colormode !== 'Colormaps') {
        tooltip += '<br/>Color: mixed'
      }
      return tooltip
    },
    visibilityStyle(item) {
      if (item.visible) {
        return 'repeating-linear-gradient(30deg, transparent, transparent 10px)'
      } else {
        return 'repeating-linear-gradient(30deg, rgba(0,0,0,0.8), rgba(0,0,0,0.8) 7px, transparent 7px, transparent 7px, transparent 10px)'
      }
      // mixed visibility:
      // 'repeating-linear-gradient(30deg, rgba(0,0,0,0.7), rgba(0,0,0,0.7) 3px, transparent 3px, transparent 3px, transparent 10px)'
    },
    colorStyle(item) {
      if (this.$props.colormode == 'Colormaps') {
        return 'repeating-linear-gradient( -45deg, gray, gray 20px)'
      }
      if (item.mixed_color) {
        colors = ['blue', 'green']
        //colors = ['red', 'green', 'blue']
        //colors = ['red', 'green', 'blue', 'purple', 'yellow']
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
