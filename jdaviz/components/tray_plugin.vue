<template>
  <v-container style="padding-left: 24px; padding-right: 24px">
    <v-row v-if="isDisabled()">
      <span> {{ getDisabledMsg() }}</span>
    </v-row>
    <div v-else>
      <v-row>
        <div style="width: calc(100% - 32px)">
          <j-docs-link :link="link">{{ description }}</j-docs-link>
        </div>
        <div style="width: 32px">
          <j-plugin-popout :popout_button="popout_button"></j-plugin-popout>
        </div>
      </v-row>
      <slot></slot>
    </div>
  </v-container>
</template>

<script>
module.exports = {
  props: ['disabled_msg', 'description', 'link', 'popout_button'],
  methods: {
    isDisabled() {
      return this.getDisabledMsg().length > 0
    },
    getDisabledMsg() {
      return this.disabled_msg || ''
    },
  }
};
</script>

<style scoped>
  .row {
    margin-bottom: 12px !important;
  }

  .row-min-bottom-padding {
    margin-bottom: 4px !important;
  }

  .row-no-outside-padding .col:first-of-type {
    padding-left: 0px !important;
  }

  .row-no-vertical-padding-margin {
    padding-top: 0px !important;
    padding-bottom: 0px !important;
    margin-bottom: 0px !important;
    margin-top: 0px !important;
  }

  .row-no-outside-padding .col:last-of-type {
    padding-right: 0px !important;
  }

  .row-no-padding > .col {
    padding-left: 0px !important;
    padding-right: 0px !important;
  }

  .v-expansion-panel-header {
    /* tighten default padding on any sub expansion headers */
    padding: 6px !important;
  }
  
  .v-expansion-panel-header .row {
    /* override margin from above and replace with equal top and bottom margins
    for the text in the panel header */
    margin-top: 2px !important;
    margin-bottom: 2px !important;
  }
</style>
