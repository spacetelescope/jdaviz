<template>
  <span v-if="icon !== undefined">
    <v-icon v-if="String(icon).startsWith('mdi-')" size="16">
      {{icon}}
    </v-icon>
    <span v-else :class="prevent_invert_if_dark ? 'layer-viewer-icon' : 'invert-if-dark layer-viewer-icon'" :style="span_style+'; color: '+color+'; '+borderStyle">
      {{String(icon).toUpperCase()}}
    </span>
  </span>
</template>

<script>
module.exports = {
  props: ['span_style', 'color', 'icon', 'linewidth', 'linestyle', 'prevent_invert_if_dark'],
  computed: {
    borderStyle() {
      if (this.$props.linewidth > 0) { 
        return 'border-bottom: '+this.$props.linewidth+'px '+this.$props.linestyle+' '+this.$props.color
      }
      return ''
    },
  }
};
</script>

<style scoped>
.layer-viewer-icon {
  width: 20px;
  height: 20px;
  line-height: 10px;
  margin-top: 4px;
  margin-right: 2px;
  padding-top: 3px;
  text-align: center;
  font-size: 12pt;
  font-weight: bold; 
}
</style>
