<template>
  <v-toolbar-items>
    <v-dialog v-model="dialog" persistent max-width="450" @keydown.stop>
      <template v-slot:activator="{ on: dialog }">
        <v-tooltip bottom>
          <template v-slot:activator="{ on: tooltip }">
            <v-btn v-on="{...tooltip, ...dialog}" icon>
              <v-icon>mdi-collapse-all</v-icon>
            </v-btn>
          </template>
          <span>Collapse</span>
        </v-tooltip>
      </template>

      <v-card>
        <v-card-title class="headline blue lighten-4" primary-title>Cube Collapse</v-card-title>

        <v-card-text>
          <v-container>
            <v-row>
              <v-col>
                <v-select
                  :items="data_items"
                  v-model="selected_data_item"
                  label="Data"
                  hint="Select the data set to use in collapse."
                ></v-select>
              </v-col>
            </v-row>
            <v-row>
              <v-col>
                <v-select
                  :items="axes"
                  v-model="selected_axis"
                  label="Axis"
                  hint="Select the axis along with the data with be collapsed."
                ></v-select>
              </v-col>
              <v-col>
                <v-select
                  :items="funcs"
                  v-model="selected_func"
                  label="Method"
                  hint="Select the method to use in the collapse."
                ></v-select>
              </v-col>
            </v-row>
          </v-container>
        </v-card-text>
        <!-- <v-divider></v-divider> -->

        <v-card-actions>
          <div class="flex-grow-1"></div>
          <v-btn color="primary" text @click="dialog = false">Cancel</v-btn>
          <v-btn color="primary" text @click="collapse">Apply</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-toolbar-items>
</template>