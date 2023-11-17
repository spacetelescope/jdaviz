<template>
  <div>
    <v-row>
      <v-col v-for="(item, index) in items">
        <j-tooltip :tooltipcontent="tooltipContent(item)">
          <v-btn
            :rounded="item.is_subset"
            :elevation="(selected.indexOf(item.label) !== -1 || selected === item.label) ? 0 : 20 "
            @click="() => {if (!multiselect){$emit('update:selected', item.label)} else if(selected.indexOf(item.label) === -1) {$emit('update:selected', selected.concat(item.label))} else {$emit('update:selected', selected.filter(select => select != item.label))} }"
            :style="'background: '+visibilityStyle(item)+', '+colorStyle(item)"
          
          >
            <span style="color: white; text-shadow: 0px 0px 3px black">
              {{ item.icon }}
            </span>
          </v-btn>
        </j-tooltip>
      </v-col>
    </v-row>
    <v-row>
      <span>Selected: {{ selected }}</span>
    </v-row>
 </div>
</template>

<script>
module.exports = {
  props: ['items', 'selected', 'multiselect'],
  methods: {
    tooltipContent(item) {
      var tooltip = item.label
      if (!item.visible) {
        tooltip += '<br/>not visible'
      }
      if (item.mixed_color) {
        tooltip += '<br/>mixed-color'
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
      if (item.mixed_color) {
        //colors = ['blue', 'green']
        colors = ['red', 'green', 'blue']
        const strip_width = 62 / colors.length

        var style = 'repeating-linear-gradient( -30deg, '
        for ([ind, color] of colors.entries()) {
          style += color + ' '+ind*strip_width+'px, ' + color + ' '+(ind+1)*strip_width+'px'
          if (ind !== colors.length-1) {
            style += ', '
          }
        }
        style += ')'
        return style
      } else {
        return 'repeating-linear-gradient( -30deg, '+item.color+', '+item.color+' 20px)'
      }
    }
  }
};
  
</script>
