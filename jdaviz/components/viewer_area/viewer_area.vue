<template>
  <splitpanes style="height: calc(100% - 48px)">
    <pane v-for="item in items">
        <jupyter-widget :widget="item" />
    </pane>
  </splitpanes>
</template>
