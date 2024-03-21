<template>
  <j-tray-plugin
    :description="docs_description || 'Viewer and data/layer options.'"
    :link="docs_link || 'https://jdaviz.readthedocs.io/en/'+vdocs+'/'+config+'/plugins.html#plot-options'"
    @plugin-ping="plugin_ping($event)"
    :popout_button="popout_button">

    <!-- VIEWER OPTIONS -->
    <plugin-viewer-select
      :items="viewer_items"
      :selected.sync="viewer_selected"
      :multiselect.sync="viewer_multiselect"
      :show_multiselect_toggle="viewer_multiselect || viewer_items.length > 1"
      :icon_checktoradial="icon_checktoradial"
      :icon_radialtocheck="icon_radialtocheck"
      :label="viewer_multiselect ? 'Viewers' : 'Viewer'"
      :show_if_single_entry="viewer_multiselect"
      :hint="viewer_multiselect ? 'Select viewers to set options simultaneously' : 'Select the viewer to set options.'"
    />

    <plugin-layer-select
      :items="science_layer_items"
      :selected.sync="science_layer_selected"
      :multiselect="science_layer_multiselect"
      :icons="icons"
      :show_if_single_entry="true"
      :label="'Science data'"
      :hint="'Select the science data'"
    />

    <plugin-layer-select
      :items="dq_layer_items"
      :selected.sync="dq_layer_selected"
      :multiselect="dq_layer_multiselect"
      :label="'Data quality'"
      :show_if_single_entry="true"
      :hint="'Select the data quality'"
      :icons="icons"
    />

    <v-row>
    <v-select
      attach
      :menu-props="{ left: true }"
      :items="flag_map_items"
      v-model="flag_map_selected"
      label="Flag definitions"
    ></v-select>
    </v-row>

    <j-plugin-section-header>Quality Flags</j-plugin-section-header>
    <v-row style="max-width: calc(100% - 80px)">
      <v-col>
        Color
      </v-col>
      <v-col>
        <strong>Flag</strong>
      </v-col>
      <v-col>
        (Decomposed)
      </v-col>
    </v-row>
    <v-row>
      <v-expansion-panels accordion>
        <v-expansion-panel v-for="(item, index) in decoded_flags" key=":item">
          <v-expansion-panel-header v-slot="{ open }">
            <v-row no-gutters align="center" style="...">
              <v-col cols=1>
              </v-col>
                <v-col cols=2>
                <j-tooltip tipid='plugin-line-lists-color-picker'>
                  <v-menu>
                    <template v-slot:activator="{ on }">
                        <span class="color-menu"
                              :style="`background:${item.color}; cursor: pointer`"
                              @click.stop="on.click"
                        > </span>
                    </template>
                    <div @click.stop="" style="text-align: end; background-color: white">
                        <v-color-picker v-model="decoded_flags[index].color"
                                        @update:color="throttledSetColor($event.hexa)">
                        ></v-color-picker>
                    </div>
                  </v-menu>
                </j-tooltip>
              </v-col>
              <v-col>
                <div> <strong>{{item.flag}}</strong> ({{Object.keys(item.decomposed).join(', ')}})</div>
              </v-col>
          </v-row>
          </v-expansion-panel-header>
          <v-expansion-panel-content>
              <v-col v-for="(item, key, index) in item.decomposed">
                <span>{{item.name}} ({{key}}): {{item.description}}</span>
              </v-col>
          </v-expansion-panel-content>
        <v-expansion-panel>
      </v-expansion-panels>
    </v-row>
  </j-tray-plugin>
</template>


<script>
  module.exports = {
    created() {
      this.throttledSetColor = _.throttle(
        (v) => { this.color = v },
        100);
    }
  }
</script>

<style>
  .v-slider {
    margin: 0px !important;
  }

  .color-menu {
      font-size: 16px;
      padding-left: 16px;
      border: 2px solid rgba(0,0,0,0.54);
  }
</style>
