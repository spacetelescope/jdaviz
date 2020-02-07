<template>
  <splitpanes :horizontal="horizontal">
    <pane v-for="(stack, i) in stacks">
      <jupyter-widget :widget="stack" />
    </pane>
  </splitpanes>
</template>