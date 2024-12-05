<template>
  <div style="width: 100%">
    <plugin-input-header
      :label="label"
      :api_hint="api_hint && api_hint + value"
      :api_hints_enabled="api_hints_enabled"
    ></plugin-input-header>
    <glue-throttled-slider
      :wait="wait"
      :min="min !== undefined ? min : 0"
      :max="max !== undefined ? max : 1"
      :step="step !== undefined ? step : 0.01"
      :value.sync="value"
      @update:value="$emit('update:value', $event)"
      hide-details
      class="no-hint"
    />
  </div>
</template>

<script>
  module.exports = {
    props: ['label', 'api_hint', 'api_hints_enabled', 'wait', 'min', 'max', 'step', 'value'],
  };
</script>
