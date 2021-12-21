<template>
  <j-tray-plugin>
    <v-row>
      <j-docs-link :link="'https://jdaviz.readthedocs.io/en/'+vdocs+'/'+config+'/plugins.html#line-lists'">Plot lines from preset or custom line lists.</j-docs-link>
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
                  <v-text-field
                    label="Unit"
                    v-model="custom_unit"
                    dense
                  >
                  </v-text-field>
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
                        <span style="overflow-wrap: anywhere; color: rgba(0, 0, 0, 0.87); font-size: 10pt">
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
