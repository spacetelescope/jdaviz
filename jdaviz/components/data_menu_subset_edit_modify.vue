<template>
  <v-menu
    open-on-hover
    right
    offset-x
    nudge-left="16"
    nudge-top="12"
    >
    <template v-slot:activator="{ on, attrs }">
      <span
        style="cursor: default; width: 100%"
        v-bind="attrs"
        v-on="on"
      >
        {{ mode }}
      </span>
    </template>
    <v-list dense>
      <v-list-item>
        <v-list-item-content>
          here
        </v-list-item-content>
      </v-list-item>
    </v-list>
  </v-menu>
</template>

<script>
module.exports = {
  props: ['mode'],
};
</script>

<style scoped>
  .v-list-item__icon, .v-list-item__content, .v-list-item__action {
    /* even denser than dense */
    padding-top: 2px !important;
    padding-bottom: 2px !important;
    margin-top: 0px !important;
    margin-bottom: 0px !important;
  }
</style>