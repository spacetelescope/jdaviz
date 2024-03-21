<template>
  <v-btn :disabled="spinner || disabled"
    text
    :color=buttonColor
    @click="$emit('click')"
  >
    <v-progress-circular
      v-if="spinner"
      indeterminate
      color="primary"
      size="20"
      width="3"
      style="margin-right: 4px"
    ></v-progress-circular>
    <span v-if="spinner === false" style="width: 24px"></span>
    <slot/>
  </v-btn>
</template>

<script>
module.exports = {
  props: ['spinner', 'disabled', 'results_isolated_to_plugin'],
  computed: {
    buttonColor() {
      if (this.results_isolated_to_plugin) {
        return this.$vuetify.theme.dark
          ? this.$vuetify.theme.themes.dark.primary
          : this.$vuetify.theme.themes.light.primary;
      } else {
        return this.$vuetify.theme.dark
          ? this.$vuetify.theme.themes.dark.accent
          : this.$vuetify.theme.themes.light.accent;
      }
    }
  }
};
</script>
