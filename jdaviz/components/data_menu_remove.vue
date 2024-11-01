<template>
  <v-menu
    absolute
    offset-y
    left
  >
    <template v-slot:activator="{ on, attrs }">
      <j-tooltip
        :span_style="'display: inline-block; float: right; ' + (delete_enabled ? '' : 'cursor: default;')"
        :tooltipcontent="delete_tooltip"
      >
        <v-btn
            icon
            v-bind="attrs"
            v-on="on"
            :disabled="!delete_enabled"
            >
            <v-icon class="invert-if-dark">mdi-delete</v-icon>
        </v-btn>
      </j-tooltip>
    </template>
    <v-list dense style="width: 200px">
      <v-list-item>
        <v-list-item-content>
          <j-tooltip tooltipcontent="Remove from this viewer only">
            <span
              style="cursor: pointer; width: 100%"
              @click="() => {$emit('remove-from-viewer')}"
            >
              Remove from viewer
            </span>
          </j-tooltip>
        </v-list-item-content>
      </v-list-item>
      <v-list-item>
        <v-list-item-content>
          <j-tooltip tooltipcontent="Remove from all viewers and application (permanent)">
            <span
              style="cursor: pointer; width: 100%"
              @click="() => {$emit('remove-from-app')}"
            >
              Remove from app
            </span>
          </j-tooltip>
        </v-list-item-content>
      </v-list-item>
    </v-list>
  </v-menu>
</template>

<script>
module.exports = {
  props: ['delete_enabled', 'delete_tooltip'],
};
</script>