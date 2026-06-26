<template>
  <j-tooltip tipid='plugin-popout'>
    <jupyter-widget v-if="popout_button_key" :widget="popout_button" :key="popout_button_key"></jupyter-widget>
  </j-tooltip>
</template>

<script>
export default {
  props: ['popout_button'],
  computed: {
    popout_button_key() {
      if (typeof this.popout_button === 'string') {
        return this.popout_button;
      }
      return this.popout_button && this.popout_button.model_id ? this.popout_button.model_id : '';
    },
  },
};
</script>
