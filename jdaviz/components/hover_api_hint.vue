<template>
  <v-list-item
  >
    <div class="v-list-item-content">
        <span class="api-hint">
        {{ hover_api_hint }}
        </span>
    </div>
    <v-list-item-action style="margin-right: -8px">
      <j-tooltip
        tooltipcontent="toggle whether API hints persist after hovering to allow for copying text"
      >
        <v-btn
          small
          variant="text"
          width="24"
          :style="lock_hover_api_hint ? 'background-color: #c7510996 !important' : null"
          @click="(e) => {e.stopPropagation(); $emit('update:lock_hover_api_hint', !lock_hover_api_hint); $emit('update:hover_api_hint', '')}"
        >
          <img
            :src="icons['api-lock']"
            width="20"
            class="invert-if-dark"/>
        </v-btn>
      </j-tooltip>
    </v-list-item-action>
  </v-list-item>
</template>

<script>
  export default {
    props: ['hover_api_hint', 'lock_hover_api_hint', 'icons'],
  };
</script>
