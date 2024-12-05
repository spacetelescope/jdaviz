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
          <j-tooltip
            :tooltipcontent="delete_viewer_tooltip"
          >
            <span
              style="cursor: pointer; width: 100%"
              :class="api_hints_enabled ? 'api-hint' : ''"
              @click="() => {$emit('remove-from-viewer')}"
            >
              {{ api_hints_enabled ?
                'dm.remove_from_viewer()'
                :
                'Remove from viewer'
              }}
            </span>
          </j-tooltip>
        </v-list-item-content>
      </v-list-item>
      <v-list-item>
        <v-list-item-content>
          <j-tooltip
            :span_style="'display: inline-block; float: right; ' + (delete_app_enabled ? '' : 'cursor: default;')"
            :tooltipcontent="delete_app_tooltip"
          >
            <span
              :style="'width: 100%; ' + (delete_app_enabled ? 'cursor: pointer;' : '')"
              :class="api_hints_enabled ? 'api-hint' : ''"
              :disabled="!delete_app_enabled"
              @click="() => {if (delete_app_enabled) {$emit('remove-from-app')}}"
            >
            {{ api_hints_enabled ?
                'dm.remove_from_app()'
                :
                'Remove from app'
              }}
            </span>
          </j-tooltip>
        </v-list-item-content>
      </v-list-item>
    </v-list>
  </v-menu>
</template>

<script>
module.exports = {
  props: ['delete_enabled', 'delete_tooltip', 'delete_viewer_tooltip', 'delete_app_enabled', 'delete_app_tooltip', 'api_hints_enabled'],
};
</script>