<template>
  <v-list-item
  >
    <v-list-item-content>
        <span class="api-hint">
        {{ hover_api_hint }}
        </span>
    </v-list-item-content>
    <v-list-item-action>
      <j-tooltip
        tooltipcontent="toggle whether API hints persist after hovering to allow for copying text"
      >
        <v-badge
          overlap
          bottom
          color="#007BA1"
          :icon="lock_hover_api_hint ? 'mdi-lock-outline' : 'mdi-lock-open-outline'"
        >
          <v-btn
            icon
            small
            @click="(e) => {e.stopPropagation(); $emit('update:lock_hover_api_hint', !lock_hover_api_hint); $emit('update:hover_api_hint', '')}"
          >
            <v-icon
              :color="lock_hover_api_hint ? '#007BA1' : null"
            >
              mdi-code-tags
            </v-icon>
          </v-btn>
        </v-badge>
      </j-tooltip>
    </v-list-item-action>
  </v-list-item>
</template>

<script>
  module.exports = {
    props: ['hover_api_hint', 'lock_hover_api_hint'],
  };
</script>