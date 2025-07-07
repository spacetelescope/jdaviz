<template>
  <j-tray-plugin
    :config="config"
    plugin_key="Markers"
    :description="docs_description"
    :link="docs_link || 'https://jdaviz.readthedocs.io/en/'+vdocs+'/'+config+'/plugins.html#markers'"
    :uses_active_status="uses_active_status"
    @plugin-ping="plugin_ping($event)"
    :keep_active.sync="keep_active"
    :popout_button="popout_button"
    :scroll_to.sync="scroll_to">

    <div class="jd-plugin-section">
      <div style="font-weight: bold; margin-bottom: 5px;">Markers Table</div>
      <div class="text--secondary" style="margin-bottom: 10px;">
        Press 'm' to create a marker.
      </div>
      <jupyter-widget :widget="table_widget"></jupyter-widget>
    </div>

    <v-divider class="my-4"></v-divider>

    <div class="jd-plugin-section">
      <div style="font-weight: bold; margin-bottom: 5px;">Distance Tool</div>
      <div class="text--secondary" style="margin-bottom: 10px;">
        Press 'd' twice to measure; hold 'd' + 'option'/'alt' to snap.
      </div>
      <div>
        <b>Distance:</b> {{ distance_display }}
      </div>
    </div>

    <v-divider class="my-4"></v-divider>

    <div class="jd-plugin-section">
      <div style="font-weight: bold; margin-bottom: 5px;">Measurements Table</div>
      <jupyter-widget :widget="measurements_table"></jupyter-widget>
    </div>

  </j-tray-plugin>
</template>
