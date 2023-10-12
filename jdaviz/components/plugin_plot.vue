<template>
  <div class="plugin-plot-component" style="margin-bottom: 40px">
    <v-row dense style="margin: 0px 0px -8px 0px !important">
      <jupyter-widget class='plugin-nested-toolbar' :widget="toolbar"></jupyter-widget>
      <v-spacer></v-spacer>
      <div style="line-height: 40px; width=32px" class="only-show-in-tray">
        <j-plugin-popout :popout_button="popout_button"></j-plugin-popout>
      </div>
    </v-row>

    <v-row style="margin: -16px 0px 8px 0px !important">
      <jupyter-widget :widget="figure" style="height: 100%; width: 100%" />
    </v-row>
  </div>
</template>

<script>
</script>

<style scoped>
  .only-show-in-tray {
    display: none;
  }
  .tray-plugin .only-show-in-tray {
    display: inline-block;
  }

  .plugin-plot-component {
    margin: 12px;
  }
  .tray-plugin .plugin-plot-component {
    margin: 0px;
    width: 100%;
    height: 480px;
  }
</style>
