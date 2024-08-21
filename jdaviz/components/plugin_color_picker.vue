<template>
  <div>
    <plugin-input-header
      v-if="label && !label_inline"
      :label="label"
      :api_hint="api_hint + '\''+value+'\''"
      :api_hints_enabled="api_hints_enabled"
    ></plugin-input-header>
    <v-menu>
      <template v-slot:activator="{ on }">
          <span class="color-menu"
                :style="`background:${value}; cursor: pointer`"
                @click.stop="on.click"
          >&nbsp;</span>
      </template>
      <div @click.stop="" style="text-align: end; background-color: white">
          <v-color-picker :value="value"
                          @update:color="$emit('color-update', $event)"></v-color-picker>
      </div>
    </v-menu>
    <span
      v-if="label && label_inline"
      style="padding-left: 12px; padding-top: 3px"
      :class="api_hints_enabled ? 'api-hint' : null"
    >
      {{  api_hints_enabled ?
          api_hint + value
          :
          label
      }}
    </span>
  </div>
</template>

<script>
  module.exports = {
    props: ['label', 'label_inline', 'api_hint', 'api_hints_enabled', 'value'],
  };
</script>
