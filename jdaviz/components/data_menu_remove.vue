<template>
  <v-menu
    absolute
    location="bottom start"
  >
    <template v-slot:activator="{ props }">
      <j-tooltip
        :span_style="'display: inline-block; float: right; ' + (delete_enabled ? '' : 'cursor: default;')"
        :tooltipcontent="delete_tooltip"
      >
        <v-btn
            icon
            variant="text"
            size="small"
            density="default"
            v-bind="props"

            :disabled="!delete_enabled"
            >
            <v-icon class="invert-if-dark">mdi-delete</v-icon>
        </v-btn>
      </j-tooltip>
    </template>
    <v-list density="compact" style="width: 200px">
      <v-list-item>
        <div class="v-list-item-content">
          <j-tooltip
            :tooltipcontent="delete_viewer_tooltip"
          >
            <span
              style="cursor: pointer; width: 100%"
              @click="() => {$emit('remove-from-viewer')}"
            >
              <j-api-hint v-if="api_hints_enabled">dm.remove_from_viewer()</j-api-hint>
              <template v-else>Remove from viewer</template>
            </span>
          </j-tooltip>
        </div>
      </v-list-item>
      <v-list-item>
        <div class="v-list-item-content">
          <j-tooltip
            :tooltipcontent="delete_app_tooltip"
          >
            <span
              :style="'width: 100%; ' + (delete_app_enabled ? 'cursor: pointer;' : '')"
              :disabled="!delete_app_enabled"
              @click="() => {if (delete_app_enabled) {$emit('remove-from-app')}}"
            >
              <j-api-hint v-if="api_hints_enabled">dm.remove_from_app()</j-api-hint>
              <template v-else>Delete from app</template>
            </span>
          </j-tooltip>
        </div>
      </v-list-item>
    </v-list>
  </v-menu>
</template>

<script>
export default {
  props: ['delete_enabled', 'delete_tooltip', 'delete_viewer_tooltip', 'delete_app_enabled', 'delete_app_tooltip', 'api_hints_enabled'],
};
</script>
