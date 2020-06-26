<template>
  <v-card flat tile>
    <v-card>
      <v-card-subtitle>Preset Line Lists</v-card-subtitle>
      <v-card-text>
        <v-container>
          <v-row
            align="start"
          >
            <v-col>
              <v-select
                :items="available_lists"
                @change="list_selected"
                label="Available Line Lists"
                hint="Select a line list to load"
                persistent-hint
              ></v-select>
            </v-col>
          </v-row>
          <v-row
            justify="end"
          >
            <v-btn color="primary" text @click="load_list">Load List</v-btn>
          </v-row>
        </v-container>
      </v-card-text>
      <v-divider></v-divider>

      <v-card-subtitle>Loaded Lines</v-card-subtitle>
      <v-card-text>
        <v-expansion-panels>
          <v-expansion-panel v-for="item in loaded_lists" key=":item">
            <v-expansion-panel-header v-slot="{ open }">
              <v-row no-gutters align="center">
                <v-col cols=1>
                  <v-btn 
                    v-if="item != 'Custom'" 
                    @click.native.stop="remove_list(item)" 
                    icon
                  >
                    <v-icon>mdi-close-circle</v-icon>
                  </v-btn>
                </v-col>
                <v-col cols=2></v-col>
                <v-col cols=8 class="text--secondary">
                  <span>{{ item }}</span>
                </v-col>
              </v-row>
            </v-expansion-panel-header>
            <v-expansion-panel-content>
              <v-row 
                v-if="item == 'Custom'"
                align="center"
                justify="center"
              >
                <v-col>
                  <v-text-field
                    label="Line Name"
                    v-model="custom_name"
                  >
                  </v-text-field>
                </v-col>
                <v-col>
                  <v-text-field
                    label="Rest Value"
                    v-model="custom_rest"
                  >
                  </v-text-field>
                </v-col>
                <v-col>
                  <v-text-field
                    label="Unit"
                    v-model="custom_unit"
                  >
                  </v-text-field>
                </v-col>
                <v-col>
                  <v-btn color="primary" text @click="add_custom_line">Add Line</v-btn>
                </v-col>
              </v-row>
              <v-row justify="space-around">
                <v-color-picker
                  hide-inputs
                  mode="hexa"
                  flat
                  @update:color="set_color({listname:item, color: $event.hexa})">
                </v-color-picker>
              </v-row
                align="center"
                justify="center"
              >
                <v-btn 
                 color="primary" 
                 text @click="show_all_in_list(item)">Show All</v-btn>
                <v-btn 
                 color="primary" 
                 text @click="hide_all_in_list(item)">Hide All</v-btn>
              <v-row>
              </v-row>
              <v-row
                justify="center"
                align="center"
                no-gutters
              >
                <v-col cols=1></v-col>
                <v-col cols=3>
                  <p class="font-weight-bold">Line Name</p>
                </v-col>
                <v-col cols=3>
                  <p class="font-weight-bold">Rest Value</p>
                </v-col>
                <v-col cols=3>
                  <p class="font-weight-bold">Unit</p>
                </v-col>
                <v-col cols=2>
                  <p class="font-weight-bold">Visible</p>
                </v-col>
              </v-row>
              <v-row
                justify="center"
                align="center"
                no-gutters
                v-for="line in list_contents[item].lines"
              >
                <v-col cols=1></v-col>
                <v-col cols = 3>
                  {{ line.linename }}
                </v-col>
                <v-col cols = 3>
                  {{ line.rest }}
                </v-col>
                <v-col cols=3>
                  {{ line.unit }}
                </v-col>
                <v-col cols=2>
                  <v-checkbox v-model="line.show" @change="change_visible(line)">
                  </v-checkbox>
                </v-col>
              </v-row>
            </v-expansion-panel-content>
          <v-expansion-panel>
        </v-expansion-panels>
      </v-card-text>
      <v-divider></v-divider>

      <v-card-text>
        <v-container>
          <v-row
            justify="left"
            align="center"
            no-gutters>
            <v-btn color="primary" text @click="plot_all_lines">Plot All</v-btn>
            <v-btn color="primary" text @click="erase_all_lines">Erase All</v-btn>
          </v-row>
        </v-container>
      </v-card-text>
    </v-card>
  </v-card>
</template>
