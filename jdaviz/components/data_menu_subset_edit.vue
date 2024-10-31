<template>
  <v-menu
    absolute
    offset-y
    bottom
    left
  >
    <template v-slot:activator="{ on, attrs }">
      <j-tooltip
        v-if="selected_n_subsets > 0"
        :span_style="'display: inline-block; float: right; ' + (subset_edit_enabled ? '' : 'cursor: default;')"
        :tooltipcontent="subset_edit_tooltip"
      >
        <v-btn
          text
          v-bind="attrs"
          v-on="on"
          :disabled="!subset_edit_enabled"
        >
          Edit Subset
        </v-btn>
      </j-tooltip>
    </template>
    <v-list dense style="width: 200px">
      <v-list-item>
        <v-list-item-content>
          <j-tooltip tooltipcontent="Select as active for interactive resizing in viewer (COMING SOON)">
            <span
              style="cursor: default; width: 100%"
              @click="() => {alert('coming soon!')}"
            >
              Resize in viewer
            </span>
          </j-tooltip>
        </v-list-item-content>
      </v-list-item>
      <v-list-item>
        <v-list-item-content>
          <j-tooltip tooltipcontent="Open in Subset Tools plugin">
            <span
              style="cursor: pointer; width: 100%"
              @click="() => {$emit('view-info')}"
            >
              Edit in plugin
            </span>
          </j-tooltip>
        </v-list-item-content>
      </v-list-item>

      <v-divider></v-divider>

      <v-list-item v-for="mode in ['replace', 'add', 'and', 'xor', 'remove']">
        <v-list-item-content>
          <data-menu-subset-edit-modify
            :mode="mode"
          />
        </v-list-item-content>
      </v-list-item>

    </v-list>
  </v-menu>
</template>

<script>
module.exports = {
  props: ['subset_edit_enabled', 'subset_edit_tooltip', 'selected_n_subsets'],
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