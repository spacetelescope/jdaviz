<template>
  <span v-if="icon !== undefined">
    <v-icon v-if="String(icon).startsWith('mdi-')" :size="icon_size || 16" :color="color">
      {{icon}}
    </v-icon>
    <span v-else-if="icons && Object.keys(icons).indexOf(icon) !== -1">
      <img :src="icons[icon]" :width="icon_size || 16"/>
    </span>
    <span v-else :class="prevent_invert_if_dark ? 'layer-viewer-icon' : 'invert-if-dark layer-viewer-icon'" :style="span_style+'; color: '+color+'; '+borderStyle">
      {{String(icon).toUpperCase()}}
    </span>
  </span>
</template>

<script>
export default {
  props: ['span_style', 'color', 'icon', 'icons', 'icon_size', 'linewidth', 'linestyle', 'prevent_invert_if_dark'],
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
  display: inline-flex;
  align-items: center;
  justify-content: center;
  vertical-align: middle;
  box-sizing: border-box;
  width: 20px;
  min-width: 20px;
  height: 20px;
  line-height: 1;
  margin-top: 0;
  margin-right: 2px;
  padding-top: 0;
  text-align: center;
  font-size: 12px;
  font-weight: bold;
}
</style>
