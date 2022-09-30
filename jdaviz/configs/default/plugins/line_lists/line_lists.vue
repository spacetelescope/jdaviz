<template>
  <j-tray-plugin
    description='Plot lines from preset or custom line lists.'
    :link="'https://jdaviz.readthedocs.io/en/'+vdocs+'/'+config+'/plugins.html#line-lists'"
    :disabled_msg="disabled_msg"
    :popout_button="popout_button">

    <j-plugin-section-header>Identified Line</j-plugin-section-header>
    <v-row>
      <j-docs-link>Highlight a line and identify its name by using the line selection tool in the spectrum viewer.</j-docs-link>
    </v-row>
    <v-row v-if="rs_enabled">
      <j-tooltip v-if='identify_label' tipid='plugin-line-lists-line-identify-chip-active'>
        <v-chip
          v-if="identify_label"
          label=true
          @click="set_identify(null)">
          <img class="color-to-accent" :src="identify_line_icon" width="20"/> {{ identify_label }}
        </v-chip>
      </j-tooltip>
      <j-tooltip v-else tipid='plugin-line-lists-line-identify-chip-inactive'>
        <v-chip label=true>
          <img class="invert-if-dark" :src="identify_line_icon" width="20"/> no line selected
        </v-chip>
      </j-tooltip>
    </v-row>

    <j-plugin-section-header>Redshift</j-plugin-section-header>
    <v-row>
      <j-docs-link>Shift spectral lines according to a specific redshift. Only enabled if at least one line is plotted.</j-docs-link>
    </v-row>
    <v-row style='margin-bottom: 0px'>
      <!-- colors are app.vue primary and toolbar colors -->
      <v-slider
        :value="rs_slider"
        @input="throttledSlider"
        @end="slider_reset"
        class="align-center"
        :max="rs_slider_half_range"
        :min="-rs_slider_half_range"
        :step="rs_slider_step"
        color="#00617E"
        track-color="#00617E"
        thumb-color="#153A4B"
        hide-details
        :disabled="!rs_enabled"
      >
      </v-slider>
    </v-row>
    <v-row style='margin-top: -24px'>
      <span class='text--secondary' style='max-width: 30%; white-space: nowrap;'>-{{rs_slider_half_range}}</span>
      <v-spacer/>
      <span class='text--secondary' style='max-width: 30%; white-space: nowrap;'>+{{rs_slider_half_range}}</span>
    </v-row>

    <v-row class="row-no-outside-padding row-min-bottom-padding">
      <v-col>
        <v-text-field
          :value='rs_redshift'
          @input='setRedshiftFloat'
          @blur="unpause_tables"
          :step="rs_slider_step"
          class="mt-0 pt-0"
          type="number"
          label="Redshift"
          hint="Redshift"
          :disabled="!rs_enabled"
        ></v-text-field>
      </v-col>
      <v-col cols=3>
        <span></span>
      </v-col>
    </v-row>

    <v-row class="row-no-outside-padding">
      <v-col>
        <v-text-field
          v-model="rs_rv"
          @input='setRVFloat'
          @blur="unpause_tables"
          :step="rs_rv_step"
          class="mt-0 pt-0"
          type="number"
          label="RV"
          hint="Redshift in RV (km/s)"
          :disabled="!rs_enabled"
        ></v-text-field>
      </v-col>
      <v-col cols=3>
        <span :class="[rs_enabled ? 'text--primary' : 'text--secondary']">km/s</span>
      </v-col>
    </v-row>
  
    <j-plugin-section-header>Preset Line Lists</j-plugin-section-header>
    <v-row>
      <v-select
        :menu-props="{ left: true }"
        attach
        :items="available_lists"
        @change="list_selected"
        label="Available Line Lists"
        hint="Select a line list to load. Toggle visibility of loaded lines in section below."
        persistent-hint
      ></v-select>
    </v-row>

    <v-row justify="end">
      <j-tooltip tipid='plugin-line-lists-load'>
        <v-btn color="primary" text @click="load_list">Load List</v-btn>
      </j-tooltip>
    </v-row>


    <j-plugin-section-header>Loaded Lines</j-plugin-section-header>
    <v-row>
      <v-expansion-panels accordion>
        <v-expansion-panel v-for="item in loaded_lists" key=":item">
          <v-expansion-panel-header v-slot="{ open }">
            <v-row no-gutters align="center" style="max-width: calc(100% - 26px)">
              <v-col cols=2>
                <v-btn 
                  v-if="item != 'Custom'" 
                  @click.native.stop="remove_list(item)" 
                  small="true"
                  icon
                >
                  <v-icon>mdi-close-circle</v-icon>
                </v-btn>
              </v-col>
              <v-col cols=2>
                <j-tooltip tipid='plugin-line-lists-color-picker'>
                  <v-menu>
                    <template v-slot:activator="{ on }">
                        <span class="linelist-color-menu"
                              :style="`background:${list_contents[item].color}`"
                              @click.stop="on.click"
                        >&nbsp;</span>
                    </template>
                    <div @click.stop="" style="text-align: end; background-color: white">
                        <v-color-picker :value="list_contents[item].color"
                                    @update:color="throttledSetColor({listname:item, color: $event.hexa})"></v-color-picker>
                    </div>
                  </v-menu>
                </j-tooltip>
              </v-col>
              <v-col cols=8>
                <div>{{ item }}</div>
              </v-col>


            </v-row>
          </v-expansion-panel-header>
          <v-expansion-panel-content style="padding-left: 0px">

            <div v-if="item == 'Custom'" style="padding-top: 16px">
              <v-row class="row-min-bottom-padding" style="display: block">
                  <j-tooltip tipid='plugin-line-lists-line-name'>
                    <v-text-field
                      label="Line Name"
                      v-model="custom_name"
                      dense
                    >
                    </v-text-field>
                  </j-tooltip>
              </v-row>

              <v-row class="row-min-bottom-padding" style="display: block">
                <j-tooltip tipid='plugin-line-lists-custom-rest'>
                  <v-text-field
                    label="Rest Value"
                    v-model="custom_rest"
                    dense
                  >
                  </v-text-field>
                </j-tooltip>
              </v-row>

              <v-row class="row-min-bottom-padding" style="display: block">
                <j-tooltip tipid='plugin-line-lists-custom-unit'>
                    <v-select
                      :menu-props="{ left: true }"
                      attach
                      :items="custom_unit_choices"
                      v-model="custom_unit"
                      label="Unit"
                      dense
                    ></v-select>
                </j-tooltip>
              </v-row>

              <v-row justify="end">
                <j-tooltip tipid='plugin-line-lists-add-custom-line'>
                  <v-btn color="primary" text @click="add_custom_line">Add Line</v-btn>
                </j-tooltip>
              </v-row>
            </div>

            <div v-if="list_contents[item].lines.length">

              <v-row class="row-no-padding" style="margin-top: 4px">
                <v-col cols=6 style="padding: 0">
                  <j-tooltip tipid='plugin-line-lists-plot-all-in-list'>
                    <v-btn
                      tile
                      :elevation=0
                      x-small
                      dense 
                      color="turquoise"
                      dark
                      style="padding-left: 8px; padding-right: 6px;"
                      @click="show_all_in_list(item)">
                      <v-icon left small dense style="margin-right: 2px">mdi-eye</v-icon>
                      Plot All
                    </v-btn>
                  </j-tooltip>
                </v-col>
                <v-col cols=6 style="text-align: right; padding: 0">
                  <j-tooltip tipid='plugin-line-lists-erase-all-in-list'>
                    <v-btn
                      tile
                      :elevation=0
                      x-small
                      dense
                      color="turquoise"
                      dark
                      style="padding-left: 8px; padding-right: 6px;"
                      @click="hide_all_in_list(item)">
                      <v-icon left small dense style="margin-right: 2px">mdi-eye-off</v-icon>
                      Erase All                     
                    </v-btn>
                  </j-tooltip>
                </v-col>
              </v-row>

              <v-row>
                <j-tooltip tipid='plugin-line-lists-spectral-range'>
                  <v-btn
                    icon
                    @click="filter_range = !filter_range"
                    style="width: 30px; margin-top: 4px"
                    ><img :class="filter_range ? 'color-to-accent' : 'invert-if-dark'" :src="filter_range_icon"/>
                    
                  </v-btn>
                </j-tooltip>

                <v-text-field
                  v-model="lines_filter"
                  append-icon='mdi-magnify'
                  style="padding: 0px 0px; margin-left: 8px; max-width: calc(100% - 38px)"
                  clearable
                  hide-details
                ></v-text-field>
              </v-row>

              <v-row>
                <span class='text--primary' style="overflow-wrap: anywhere; font-size: 10pt;">
                  <b>Medium: {{list_contents[item].medium}}</b>
                </span>                    
              </v-row>

              <v-divider style="margin-bottom: 8px"></v-divider>

              <v-row v-for="(line, line_ind) in list_contents[item].lines" style="margin-bottom: 0px !important;">
                <div v-if="lineItemVisible(line, lines_filter, filter_range)">
                  
                  <v-row class="row-no-vertical-padding-margin" style="margin: 0px">
                    <v-col cols=7  style="padding: 0">
                      <span class='text--primary' style="overflow-wrap: anywhere; font-size: 16pt; padding-top: 3px;">
                        <b>{{line.linename}}</b>
                      </span>                    
                    </v-col>
                    
                    <v-col cols=2 align="right" style="padding: 0">
                      <j-tooltip tipid='plugin-line-lists-line-identify'>
                        <v-btn icon @click="set_identify([item, line, line_ind])">
                          <img :class="line.identify ? 'color-to-accent' : 'invert-if-dark'" :src="identify_line_icon" width="20"/>
                        </v-btn>
                      </j-tooltip>
                    </v-col>
                    <v-col cols=3 align="right" style="padding: 0">
                      <j-tooltip tipid='plugin-line-lists-line-visible'>
                        <v-btn :color="line.show ? 'accent' : 'default'" icon @click="change_visible([item, line, line_ind])">
                          <v-icon>{{line.show ? "mdi-eye" : "mdi-eye-off"}}</v-icon>
                        </v-btn>
                      </j-tooltip style="padding: 0">
                    </v-col>

                  </v-row>
                  <v-row class="row-min-bottom-padding" >
                    <v-col cols=6 style="padding-bottom: 3px; padding-top: 0px">
                      <v-subheader class="pl-0 slider-label" style="height: 16px"><b>Rest</b/></v-subheader>
                      <v-text-field
                        v-model="line.rest"
                        class="mt-0 pt-0"
                        dense
                        :hint="line.unit"
                        persistent-hint
                        disabled
                      ></v-text-field>
                    </v-col>
                    <v-col cols=6 style="padding-top: 0px">
                      <v-subheader class="pl-0 slider-label" style="height: 16px"><b>Observed</b/></v-subheader>
                      <v-text-field
                        v-model="line.obs"
                        @input="(e) => change_line_obs({list_name: item, line_ind: line_ind, obs_new: parseFloat(e), avoid_feedback: true})"
                        @blur="unpause_tables"
                        step="0.1"
                        class="mt-0 pt-0"
                        dense
                        type="number"
                        :hint="line.unit"
                        persistent-hint
                      ></v-text-field>
                    </v-col>
                  </v-row>
                </div>
              </v-row>
            </div>
          </v-expansion-panel-content>
        <v-expansion-panel>
      </v-expansion-panels>
    </v-row>

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
            @click="plot_all_lines">
            <v-icon left small dense style="margin-right: 2px">mdi-eye</v-icon>
            Plot All
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
            @click="erase_all_lines">
            <v-icon left small dense style="margin-right: 2px">mdi-eye-off</v-icon>
            Erase All                     
          </v-btn>  
        </j-tooltip>
      </v-col>

    </v-row>

  </j-tray-plugin>
</template>

<script>
  module.exports = {
    methods: {
      lineItemVisible(lineItem, lines_filter, filter_range) {       
        if (lines_filter === null || lines_filter.length == 0) {
          text_filter = true
        }
        else{
          // simple exact text search match on the line name for now.
          text_filter = lineItem.linename.toLowerCase().indexOf(lines_filter.toLowerCase()) !== -1
        }

        if (filter_range) {
          in_range = (lineItem.obs > this.spectrum_viewer_min) && (lineItem.obs < this.spectrum_viewer_max)
        }
        else{
          in_range = true
        }

        return (text_filter && in_range)
      }
    },
    created() {
      this.throttledSlider = (v) => {
        // we want the throttle wait to be dynamic (as set by line_lists.py based
        // on the number of currently plotted lines)
        if (this.rs_slider_throttle !== this.throttledSliderCurrWait) {
          // create a new throttle function with the current wait
          if (this.throttledSliderCurr) {
            // console.log("canceling old throttle")
            this.throttledSliderCurr.cancel()
          }
          // console.log("creating new throttle with wait: ", this.rs_slider_throttle)
          this.throttledSliderCurr = _.throttle(
            (v) => { this.rs_slider = v; },
            this.rs_slider_throttle);
          this.throttledSliderCurrWait = this.rs_slider_throttle        
        }
        return this.throttledSliderCurr(v)
      },
      this.setRedshiftFloat = (v) => {
        this.rs_redshift = parseFloat(v)
      }
      this.setRVFloat = (v) => {
        this.rs_rv = parseFloat(v)
      }
      this.throttledSetColor = _.throttle(
        (v) => { this.set_color(v) },
        100);
    }
  }
</script>

<style>
  .v-slider {
    margin: 0px !important;
  }

  .linelist-color-menu {
      font-size: 16px;
      padding-left: 16px;
      border: 2px solid rgba(0,0,0,0.54);
  }
</style>
