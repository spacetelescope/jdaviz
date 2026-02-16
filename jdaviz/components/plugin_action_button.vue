<template>
  <v-btn :disabled="spinner || disabled"
    variant="text"
    :color="buttonColor"
    :class="api_hints_enabled ? 'api-hint' : null"
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
export default {
  props: ['spinner', 'disabled', 'results_isolated_to_plugin', 'api_hints_enabled'],
  computed: {
    buttonColor() {
      return this.results_isolated_to_plugin ? 'primary' : 'accent';
    }
  }
};
</script>
