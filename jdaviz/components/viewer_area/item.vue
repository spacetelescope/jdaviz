<template>
  <splitpanes :horizontal="horizontal">
    <pane v-for="(stack, i) in stacks">
      <jupyter-widget :widget="stack" />
    </pane>
    <!-- <pane v-for="(item, i) in items">
      <jupyter-widget :widget="item" />
    </pane> -->
  </splitpanes>
</template>