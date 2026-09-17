<template>
  <div>
    <plugin-input-header
      v-if="label && !label_inline"
      :label="label"
      :api_hint="api_hint + '\''+value+'\''"
      :api_hints_enabled="api_hints_enabled"
    ></plugin-input-header>
    <div style="display: flex; align-items: center">
      <v-menu>
        <template v-slot:activator="{ props }">
            <span class="color-menu"
                  :style="`background:${value}; cursor: pointer`"
                  v-bind="props"
            >&nbsp;</span>
        </template>
        <div @click.stop="" style="text-align: end; background-color: white">
            <v-color-picker :model-value="value"
                            @update:modelValue="$emit('color-update', $event)"></v-color-picker>
        </div>
      </v-menu>
      <span
        v-if="label && label_inline"
        style="padding-left: 12px"
        :class="api_hints_enabled ? 'api-hint' : null"
      >
        {{  api_hints_enabled ?
            api_hint + value
            :
            label
        }}
      </span>
    </div>
  </div>
</template>

<script>
  export default {
    props: ['label', 'label_inline', 'api_hint', 'api_hints_enabled', 'value'],
  };
</script>

<style scoped>
  .color-menu {
      display: inline-block;
      width: 24px;
      height: 24px;
      vertical-align: middle;
      border: 2px solid rgba(0,0,0,0.54);
  }
</style>
