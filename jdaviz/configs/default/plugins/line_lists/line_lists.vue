<template>
  <j-tray-plugin :disabled_msg="disabled_msg">
    <v-row>
      <j-docs-link :link="'https://jdaviz.readthedocs.io/en/'+vdocs+'/'+config+'/plugins.html#line-lists'">Plot lines from preset or custom line lists.</j-docs-link>
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
          :step="rs_redshift_step"
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
        :items="available_lists"
        @change="list_selected"
        label="Available Line Lists"
        hint="Select a line list to load"
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
            <v-row no-gutters align="center">
              <v-col cols=3>
                <v-btn 
                  v-if="item != 'Custom'" 
                  @click.native.stop="remove_list(item)" 
                  icon
                  style="width: 60%"
                >
                  <v-icon>mdi-close-circle</v-icon>
                </v-btn>
              </v-col>
              <v-col cols=9 class="text--secondary">
                <v-row>
                  <span>{{ item }}</span>
                </v-row>
              </v-col>
            </v-row>
          </v-expansion-panel-header>
          <v-expansion-panel-content style="padding-left: 0px">

            <v-row justify="space-around" style="padding-top: 16px">
              <v-color-picker
                hide-inputs
                mode="hexa"
                width="200px"
                flat
                @update:color="set_color({listname:item, color: $event.hexa})">
              </v-color-picker>
            </v-row>

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

            <v-row class="row-no-padding">
              <v-col cols=6>
                <j-tooltip tipid='plugin-line-lists-erase-all-in-list'>
                  <v-btn 
                   color="accent" 
                   style="padding-left: 8px; padding-right: 8px;"
                   text @click="hide_all_in_list(item)">Erase All</v-btn>
                </j-tooltip>
              </v-col>
              <v-col cols=6 style="text-align: right">
                <j-tooltip tipid='plugin-line-lists-plot-all-in-list'>
                  <v-btn 
                   color="accent"
                   style="padding-left: 8px; padding-right: 8px;"
                   text @click="show_all_in_list(item)">Plot All</v-btn>
                </j-tooltip>
              </v-col>
            </v-row>

            <div 
              v-if="list_contents[item].lines.length" 
              style="margin-left: -10px; margin-right: -12px"
            >
              <v-row
                justify="center"
                align="center"
                classname="row-no-outside-padding"
              >
                <v-col cols=5>
                  <p class="font-weight-bold">Name</p>
                </v-col>
                <v-col cols=7> <!-- covers rest value and unit cols below -->
                  <p class="font-weight-bold">Rest Value</p>
                </v-col>
              </v-row>
              <v-row
                justify="center"
                align="center"
                class="row-no-outside-padding"
                v-for="line in list_contents[item].lines"
              >
                <v-col cols=5>
                  <j-tooltip tipid='plugin-line-lists-line-visible'>
                    <v-checkbox v-model="line.show" @change="change_visible(line)">
                      <template v-slot:label>
                        <span class='text--primary' style="overflow-wrap: anywhere; font-size: 10pt">
                          {{line.linename}}
                        </span>
                      </template>
                    </v-checkbox>
                  </j-tooltip>
                </v-col>
                <v-col cols=4 style="font-size: 10pt">
                  {{ line.rest }}
                </v-col>
                <v-col cols=3 style="font-size: 10pt">
                  {{ line.unit.replace("Angstrom", "&#8491;") }}
                </v-col>
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
            color="accent"
            style="padding-left: 8px; padding-right: 8px;"
            text @click="erase_all_lines">Erase All</v-btn>
        </j-tooltip>
      </v-col>
      <v-col cols=6 style="text-align: right">
        <j-tooltip tipid='plugin-line-lists-plot-all'>
          <v-btn 
            color="accent"
            style="padding-left: 8px; padding-right: 8px;"
            text @click="plot_all_lines">Plot All</v-btn>
        </j-tooltip>
      </v-col>

    </v-row>

  </j-tray-plugin>
</template>

<script>
  module.exports = {
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
    }
  }
</script>

<style>
  .v-slider {
    margin: 0px !important;
  }
</style>
