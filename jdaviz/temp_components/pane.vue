<template>
  <Pane v-bind="$attrs">
    <slot />
  </Pane>
</template>

<script setup>
import { Pane } from 'https://esm.sh/splitpanes@4.0.4?bundle'
</script>
