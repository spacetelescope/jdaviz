<template>
  <j-tooltip tipid='plugin-popout'>
    <jupyter-widget :widget="popout_button"></jupyter-widget>
  </j-tooltip>
</template>

<script>
export default {
  props: ['popout_button'],
};
</script>
