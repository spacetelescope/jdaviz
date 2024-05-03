<template>
  <j-tray-plugin
    :description="docs_description || 'Data Quality layer visualization options.'"
    :link="docs_link || 'https://jdaviz.readthedocs.io/en/'+vdocs+'/'+config+'/plugins.html#data-quality'"
    @plugin-ping="plugin_ping($event)"
    :popout_button="popout_button">

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

    <v-row class="row-no-padding">
      <v-col>
        <v-subheader class="pl-0 slider-label" style="height: 12px">Data quality relative opacity</v-subheader>
        <glue-throttled-slider wait="300" min="0" max="1" step="0.01" :value.sync="dq_layer_opacity"/>
      </v-col>
    </v-row>

    <j-plugin-section-header>Quality Flags</j-plugin-section-header>
    <v-row class="row-no-padding">
      <v-col cols=6>
        <j-tooltip tipid='plugin-dq-show-all'>
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
        <j-tooltip tipid='plugin-dq-hide-all'>
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

    <v-col style="...">
      <v-row>
      <v-select
        :menu-props="{ left: true }"
        attach
        multiple
        :items="Object.keys(flag_map_definitions_selected).map(Number)"
        item-value="item => item"
        item-text="item"
        v-model="flags_filter"
        label="Filter by bits"
        hint="Any flags containing these decomposed bits will be visualized."
        persistent-hint
      >
        <template v-slot:item="{active, item, attrs, on}">
          <v-list-item v-on="on" v-bind="attrs" #default="{active}">
            <v-list-item-action>
            <v-checkbox :input-value="active"></v-checkbox>
            </v-list-item-action>
            <v-list-item-content>
              <v-list-item-title v-if="flag_map_definitions_selected[item].name.length > 0">
                {{item + ': ' + flag_map_definitions_selected[item].name}}
              </v-list-item-title>
              <v-list-item-title v-else-if="flag_map_definitions_selected[item].description.length > 25">
                {{item + ': ' + flag_map_definitions_selected[item].description.slice(0, 25) + "..."}}
              </v-list-item-title>
              <v-list-item-title v-else>
                {{item + ': ' + flag_map_definitions_selected[item].description}}
              </v-list-item-title>
            </v-list-item-content>
          </v-list-item>
        </template>
      </v-select>
      <v-col align="right">
        <v-btn text @click="clear_flags_filter" color="accent">
          Clear Filter
        </v-btn>
      </v-col>
      </v-row>
    </v-col>
    <v-row >
      <v-col cols=3 align="left">
        Color
      </v-col>
      <v-col cols=7 align="left">
        <strong>Flag</strong> (Decomposed)
      </v-col>
    </v-row>

    <v-row>
      <v-expansion-panels accordion>
        <v-expansion-panel v-for="(item, index) in decoded_flags" key=":item">
          <div v-if="flagVisible(item, item.decomposed, flags_filter)">
          <v-expansion-panel-header v-slot="{ open }">
            <v-row no-gutters align="center" style="...">
              <v-col cols=1>
              </v-col>
                <v-col cols=2>
                <j-tooltip tipid='plugin-dq-color-picker'>
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
                <v-btn :color="item.show ? 'accent' : 'default'" icon @click="toggleVisibility(index)">
                  <v-icon>{{item.show ? "mdi-eye" : "mdi-eye-off"}}</v-icon>
                </v-btn>
              </v-col>
            <v-col cols=8 align="left" style="...">
              <v-row v-for="(item, key, index) in item.decomposed">
                <span v-if="item.name !== null && item.name.length > 0"><strong>{{item.name}}</strong> ({{key}}): {{item.description}}</span>
                <span v-else><strong>{{key}}</strong>: {{item.description}}</span>
              </v-row>
            </v-col>
            </v-row>
          </v-expansion-panel-content>
        </div>
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
    toggleVisibility(index) {
      this.update_visibility(index)
    },
    flagVisible(flag_item, decomposed, flags_filter) {
      if (flags_filter === null || flags_filter.length == 0) {
        return true
      } else {
        // if any of the decomposed bits are in `flags_filter`, return true:
        return Object.keys(decomposed).filter(value => flags_filter.includes(parseInt(value))).length !== 0;
      }
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
