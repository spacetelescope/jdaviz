<template>
  <splitpanes class="fill-height">
    <pane v-for="item in items">
        <jupyter-widget :widget="item" />
    </pane>
  </splitpanes>
</template>
