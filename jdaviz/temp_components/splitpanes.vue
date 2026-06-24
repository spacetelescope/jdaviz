<template>
  <Splitpanes v-bind="$attrs">
    <slot />
  </Splitpanes>
</template>

<script setup>
import { Splitpanes } from 'https://esm.sh/splitpanes@4.0.4?external=vue'
</script>

<style>
@import url("https://unpkg.com/splitpanes@4.0.4/dist/splitpanes.css");
</style>
