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
    <v-row class="row-no-padding">
      <v-col cols=6>
        <j-tooltip tipid='plugin-line-lists-erase-all'>
          <v-btn
            tile
            :elevation=0
            x-small
            dense
            color="turquoise"
            dark
            style="padding-left: 8px; padding-right: 6px;"
            @click="show_all_flags">
            <v-icon left small dense style="margin-right: 2px">mdi-eye</v-icon>
            Show All
          </v-btn>
        </j-tooltip>
      </v-col>
      <v-col cols=6 style="text-align: right">
        <j-tooltip tipid='plugin-line-lists-plot-all'>
          <v-btn
            tile
            :elevation=0
            x-small
            dense
            color="turquoise"
            dark
            style="padding-left: 8px; padding-right: 6px;"
            @click="hide_all_flags">
            <v-icon left small dense style="margin-right: 2px">mdi-eye-off</v-icon>
            Hide All
          </v-btn>
        </j-tooltip>
      </v-col>
    </v-row>

    <v-row style="max-width: calc(100% - 80px)">
      <v-col>
        Color
      </v-col>
      <v-col cols=8>
        <strong>Flag</strong> (Decomposed)
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
                                        @update:color="throttledSetColor(index, $event.hexa)">
                        ></v-color-picker>
                    </div>
                  </v-menu>
                </j-tooltip>
              </v-col>
              <v-col cols=8>
                <div><strong>{{item.flag}}</strong> ({{Object.keys(item.decomposed).join(', ')}})</div>
              </v-col>
          </v-row>
          </v-expansion-panel-header>
          <v-expansion-panel-content>
            <v-row no-gutters style="..." align="center">
              <v-col cols=2 align="left">
                <v-btn :color="item.show ? 'accent' : 'default'" icon @click="toggle_visibility(index)">
                  <v-icon>{{item.show ? "mdi-eye" : "mdi-eye-off"}}</v-icon>
                </v-btn>
              </v-col>
            <v-col cols=8 align="left" style="...">
              <v-row v-for="(item, key, index) in item.decomposed">
                <span><strong>{{item.name}}</strong> ({{key}}): {{item.description}}</span>
              </v-row>
            </v-col>
            </v-row>
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
      (index, color) => {
        this.update_color([index, color])
      },
      100);
  },
  methods: {
    toggle_visibility(index) {
      this.update_visibility(index)
    }
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
