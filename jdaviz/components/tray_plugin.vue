<template>
  <v-container>
    <slot>
    </slot>
  </v-container>
</template>

<script>
module.exports = {
  props: {docslink: String, 
          docstext: String
        },
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
