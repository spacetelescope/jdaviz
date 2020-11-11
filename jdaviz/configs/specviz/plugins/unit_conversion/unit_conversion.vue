<template>
  <v-card flat tile>
    <v-container>
      <v-row>
        <v-col class="py-0">
          <v-text-field
            v-model="selected_data"
            label="Data"
            hint="Data to be converted."
            disabled="True"
            persistent-hint
          ></v-text-field>
        </v-col>
      </v-row>
      <v-row>
        <v-col>
          <v-text-field
            ref="current_spectral_axis_unit"
            label="Current Spectral Axis Unit"
            v-model="current_spectral_axis_unit"
            hint="The spectral axis unit of the currently selected data."
            persistent-hint
            disabled="True"
          ></v-text-field>
        </v-col>
      </v-row>
      <v-row>
        <v-col>
          <v-text-field
            ref="current_flux_unit"
            label="Current Flux Unit"
            v-model="current_flux_unit"
            hint="The flux unit of the currently selected data."
            persistent-hint
            disabled="True"
          ></v-text-field>
        </v-col>
      </v-row>
      <v-row>
        <v-col>
          <v-combobox
            label="New Spectral Axis Unit"
            :items="spectral_axis_unit_equivalencies"
            v-model="new_spectral_axis_unit"
            @input.native="new_spectral_axis_unit=$event.srcElement.value"
            return-object
            hide-no-data="True"
            hint="The spectral axis unit the currently selected data will be converted to."
            persistent-hint
          ></v-text-field>
        </v-col>
      </v-row>
      <v-row>
        <v-col>
          <v-combobox
            label="New Flux Unit"
            :items="flux_unit_equivalencies"
            v-model="new_flux_unit"
            @input.native="new_flux_unit=$event.srcElement.value"
            return-object
            hint="The flux unit the currently selected data will be converted to."
            persistent-hint
          ></v-text-field>
        </v-col>
      </v-row>
    </v-container>
    <!-- <v-divider></v-divider> -->

    <v-card-actions>
      <div class="flex-grow-1"></div>
      <v-btn :disabled="selected_data == ''"
      color="primary" text @click="unit_conversion">Apply</v-btn>
    </v-card-actions>
  </v-card>
</template>
