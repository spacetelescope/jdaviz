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
      <jupyter-widget :widget="table_widget"></jupyter-widget>
    </div>

    <v-divider class="my-4"></v-divider>

    <div class="jd-plugin-section">
      <div style="font-weight: bold; margin-bottom: 5px;">
        Distance Tool
        
        <v-tooltip bottom>
          <template v-slot:activator="{ on, attrs }">
            <v-icon
              small
              v-bind="attrs"
              v-on="on"
              class="ml-1" 
            >
              mdi-help-circle-outline
            </v-icon>
          </template>
          <span>{{ distance_tool_docs }}</span>
        </v-tooltip>
        
      </div>
      <div>{{ distance_display }}</div>
    </div>

    <v-divider class="my-4"></v-divider>

    <div class="jd-plugin-section">
      <div style="font-weight: bold; margin-bottom: 5px;">Distance Table</div>
      <jupyter-widget :widget="distances_table"></jupyter-widget>
    </div>

  </j-tray-plugin>
</template>


