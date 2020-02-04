<template>
  <splitpanes class="fill-height" horizontal>
    <pane v-for="row in viewers">
        <jupyter-widget :widget="row" />
    </pane>
  </splitpanes>
</template>
