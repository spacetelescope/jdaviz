<template>
  <j-tooltip :tooltipcontent="tooltipContent(tooltip, label, visible, colormode, colors, linewidth, is_subset)" :disabled="disabled">
    <v-btn
      :rounded="is_subset"
      @click="(e) => $emit('click', e)"
      :style="'padding: 0px; margin-bottom: 4px; background: '+visibilityBackgroundStyle(visible)+', '+colorBackgroundStyle(colors, cmap_samples)+'; '+btn_style"
      width="30px"
      min-width="30px"
      height="30px"
      :disabled="disabled"
    >
      <v-icon v-if="String(icon).startsWith('mdi-')" style="color: white">
        {{  icon }}
      </v-icon>"
      <span v-else :style="'color: white; text-shadow: 0px 0px 3px black; '+borderStyle(linewidth)">
        {{ icon }}
      </span>
    </v-btn>
  </j-tooltip>
</template>

<script>
module.exports = {
  // tooltip: undefined will use default generated, empty will skip tooltips, any other string will be used directly
  props: ['label', 'icon', 'visible', 'is_subset', 'colors', 'linewidth', 'colormode', 'cmap_samples', 'btn_style', 'tooltip', 'disabled'],
  methods: {
    tooltipContent(tooltip, label, visible, colormode, colors, linewidth, is_subset) {
      if (tooltip !== undefined) {
        return tooltip
      }
      var tooltip = label
      if (visible === 'mixed') {
        tooltip += '<br/>Visibility: mixed'
      } else if (!visible) {
        tooltip += '<br/>Visibility: hidden'
      }
      if (colormode === 'mixed' && !is_subset) {
        tooltip += '<br/>Color mode: mixed'
      }
      if (colors.length > 1) {
        if (colormode === 'Colormaps' && !is_subset) {
          tooltip += '<br/>Colormap: mixed'
        } else if (colormode === 'mixed' && !is_subset) {
          tooltip += '<br/>Color/colormap: mixed'
        } else {
          tooltip += '<br/>Color: mixed'
        }
      }
      if (linewidth == 'mixed' && !is_subset) {
        tooltip += '<br/>Linewidth: mixed'
      }
      return tooltip
    },
    visibilityBackgroundStyle(visible) {
      if (visible === 'mixed'){
        return 'repeating-linear-gradient(30deg, rgba(0,0,0,0.3), rgba(0,0,0,0.3) 3px, transparent 3px, transparent 3px, transparent 10px)'
      }
      else if (visible) {
        return 'repeating-linear-gradient(30deg, transparent, transparent 10px)'
      } else {
        return 'repeating-linear-gradient(30deg, rgba(0,0,0,0.4), rgba(0,0,0,0.4) 8px, transparent 8px, transparent 8px, transparent 10px)'
      }
    },
    colorBackgroundStyle(colors, cmap_samples) {
      const strip_width = 42 / colors.length
      var cmap_strip_width = strip_width
      var style_colors = []
      var style = 'repeating-linear-gradient( 135deg, '
  
      for ([mi, color_or_cmap] of colors.entries()) {
        if (color_or_cmap == 'from_list') {
          /* follow-up: use actual colors from the DQ plugins */
          color_or_cmap = 'rainbow'
        }
  
        if (color_or_cmap.startsWith('#')) {
          style_colors = [color_or_cmap]
        } else {
          style_colors = cmap_samples[color_or_cmap]
        }

        cmap_strip_width = strip_width / style_colors.length
        for ([ci, color] of style_colors.entries()) {
          var start = mi*strip_width + ci*cmap_strip_width
          var end = mi*strip_width+(ci+1)*cmap_strip_width
          style += color + ' '+start+'px, ' + color + ' '+end+'px'
          if (ci !== style_colors.length-1) {
            style += ', '
          }
        }
        if (mi !== colors.length-1) {
          style += ', '
        }
      }
    
      style += ')'
      return style
    },
    borderStyle(linewidth) {
      if (linewidth != 'mixed' && linewidth > 0) { 
        return 'border-bottom: '+Math.min(linewidth, 5)+'px solid white'
      }
      return ''
    },
  }
};
</script>

<style scoped>
</style>
