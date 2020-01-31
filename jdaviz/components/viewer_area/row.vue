<template>
  <splitpanes>
    <pane v-for="(col, j) in items">
        <jupyter-widget :widget="col" />
    </pane>
  </splitpanes>
</template>