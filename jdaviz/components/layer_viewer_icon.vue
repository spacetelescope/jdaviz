<template>
  <span v-if="icon !== undefined" :class="prevent_invert_if_dark ? '' : 'invert-if-dark'" :style="span_style+'; color: '+color+'; '+borderStyle">
        {{String(icon).toUpperCase()}}
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
span {
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
