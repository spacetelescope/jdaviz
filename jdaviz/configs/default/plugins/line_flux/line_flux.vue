<template>
  <v-dialog v-model="dialog" persistent max-width="450" @keydown.stop="">
    <template v-slot:activator="{ on: dialog }">
      <v-tooltip bottom>
        <template v-slot:activator="{ on: tooltip }">
          <v-btn v-on="{...tooltip, ...dialog}" icon>
            <v-icon>timeline</v-icon>
          </v-btn>
        </template>
        <span>Line Flux</span>
      </v-tooltip>
    </template>

    <v-card>
      <v-card-title class="headline blue lighten-4" primary-title>Line Flux</v-card-title>

      <v-card-text>
        <v-container>
          <v-row>
            <v-col>
              <v-select
                :items="dc_items"
                @change="data_selected"
                label="Data"
                hint="Select the data set to be smoothed."
              ></v-select>
            </v-col>
          </v-row>
          <v-row>
            <v-col>
              <v-text-field
                ref="wavelength"
                label="Line Flux at Wavelength"
                v-model="wavelength"
                hint="Line flux of the chosen wavelength."
                persistent-hint
                :rules="[() => !!stddev || 'This field is required']"
              ></v-text-field>
            </v-col>
          </v-row>
        </v-container>
      </v-card-text>
      <v-divider></v-divider>

      <v-card-actions>
        <div class="flex-grow-1"></div>
        <v-btn color="primary" text @click="dialog = false">Cancel</v-btn>
        <v-btn color="primary" text @click="line_flux">Apply</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>