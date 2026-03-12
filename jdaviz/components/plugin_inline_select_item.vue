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
    <span :class="api_hints_enabled ? 'api-hint' : null">
      <j-layer-viewer-icon v-if="item.icon && !api_hints_enabled" :icon="item.icon" :prevent_invert_if_dark="false"></j-layer-viewer-icon>
      <v-icon v-else-if="item.color && item.type && !api_hints_enabled" start :color="item.color">
        {{ item.type=='spectral' ? 'mdi-chart-bell-curve' : 'mdi-chart-scatter-plot' }}
      </v-icon>
      {{ api_hints_enabled ?
          '\'' + item.label + '\''
          :
          item.label
      }}
    </span>
  </div>
</template>

<script>
export default {
  props: ['item', 'selected', 'multiselect', 'single_select_allow_blank', 'api_hints_enabled'],
  methods: {
    isSelected() {
      if (this.multiselect) {
        return this.selected.includes(this.item.label)
      } else {
        return this.selected === this.item.label
      }
    },
    clicked() {
      let selected

      if (this.multiselect) {
        if (this.isSelected()) {
          selected = this.selected.filter(item => item !== this.item.label)
        } else {
          selected = this.selected.concat(this.item.label)
        }
      } else {
        if (this.isSelected()) {
          // TODO: setting to allow vs forbid blank
          if (this.single_select_allow_blank) {
            selected = ''
          } else {
            selected = this.selected
          }
        } else {
          selected = this.item.label
        }
      }
      this.$emit('update:selected', selected)
    }
  },
};
</script>

<style scoped>
</style>
