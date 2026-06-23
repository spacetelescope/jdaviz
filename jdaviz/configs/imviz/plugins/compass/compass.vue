<template>
  <j-tray-plugin
    :description="docs_description"
    :link="docs_link || 'https://jdaviz.readthedocs.io/en/'+vdocs+'/'+config+'/plugins.html#compass'"
    :uses_active_status="uses_active_status"
    @plugin-ping="plugin_ping($event)"
    :popout_button="popout_button"
    :scroll_to.sync="scroll_to">

    <plugin-viewer-select
      :items="viewer_items"
      :selected.sync="viewer_selected"
      label="Viewer"
      hint="Select a viewer to show."
    />

    <v-row v-if="data_label">
      <v-chip
        label=true
      >
        <j-layer-viewer-icon :icon="icon" :prevent_invert_if_dark="true"></j-layer-viewer-icon>
        {{ data_label }}
      </v-chip>
    </v-row>

    <img class='invert-in-dark' v-if="img_data" :src="`data:image/png;base64,${img_data}`" :style="'width: 100%; max-width: 400px; margin-top: 50px'" />

  </j-tray-plugin>
</template>

<style>
.theme--dark .invert-in-dark {
  filter: brightness(0.88) invert(1);
}
</style>
