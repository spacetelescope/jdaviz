<template>
  <div>
    <v-btn 
      icon
      :color="isSelected() ? 'accent' : 'default'"
      @click="clicked"
    >
        <v-icon v-if="multiselect">{{isSelected() ? "mdi-checkbox-marked" : "mdi-checkbox-blank-outline"}}</v-icon>
        <v-icon v-else>{{isSelected() ? "mdi-radiobox-marked" : "mdi-radiobox-blank"}}</v-icon>
    </v-btn>
    <span>
      <j-layer-viewer-icon v-if="item.icon" :icon="item.icon" :prevent_invert_if_dark="false"></j-layer-viewer-icon>
      <v-icon v-else-if="item.color && item.type" left :color="item.color">
        {{ item.type=='spectral' ? 'mdi-chart-bell-curve' : 'mdi-chart-scatter-plot' }}
      </v-icon>
      {{ item.label }}
    </span>
  </div>
</template>

<script>
module.exports = {
  props: ['item', 'selected', 'multiselect', 'single_select_allow_blank'],
  methods: {
    isSelected() {
      if (this.multiselect) {
        return this.selected.includes(this.item.label)
      } else {
        return this.selected === this.item.label
      }
    },
    clicked() {
      if (this.multiselect) {
        if (this.isSelected()) {
          this.selected.pop(this.item.label)
        } else {
          this.selected.push(this.item.label)
        }
      } else {
        if (this.isSelected()) {
          // TODO: setting to allow vs forbid blank
          if (this.single_select_allow_blank) {
            this.selected = ''
          }
        } else {
          this.selected = this.item.label
        }
      }
      this.$emit('update:selected', this.selected)
    }
  },
};
</script>

<style scoped>
</style>
