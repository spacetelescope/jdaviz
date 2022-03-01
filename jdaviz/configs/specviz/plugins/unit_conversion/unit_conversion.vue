<template>
  <j-tray-plugin :disabled_msg="disabled_msg">
    <v-row>
      <j-docs-link :link="'https://jdaviz.readthedocs.io/en/'+vdocs+'/'+config+'/plugins.html#unit-conversion'">Convert the spectral flux density and spectral axis units.</j-docs-link>
    </v-row>

    <v-row>
      <v-text-field
        v-model="selected_data"
        label="Data"
        hint="Data to be converted."
        disabled="True"
        persistent-hint
      ></v-text-field>
    </v-row>

    <v-row>
      <v-text-field
        ref="current_spectral_axis_unit"
        label="Current Spectral Axis Unit"
        v-model="current_spectral_axis_unit"
        hint="The spectral axis unit of the currently selected data."
        persistent-hint
        disabled="True"
      ></v-text-field>
    </v-row>

    <v-row>
      <v-text-field
        ref="current_flux_unit"
        label="Current Flux Unit"
        v-model="current_flux_unit"
        hint="The flux unit of the currently selected data."
        persistent-hint
        disabled="True"
      ></v-text-field>
    </v-row>

    <v-row>
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
    </v-row>

    <v-row>
      <v-combobox
        label="New Flux Unit"
        :items="flux_unit_equivalencies"
        v-model="new_flux_unit"
        @input.native="new_flux_unit=$event.srcElement.value"
        return-object
        hint="The flux unit the currently selected data will be converted to."
        persistent-hint
      ></v-text-field>
    </v-row>

    <v-row justify="end">
      <j-tooltip tipid='plugin-unit-conversion-apply'>
        <v-btn :disabled="selected_data == ''"
        color="accent" text @click="unit_conversion">Apply</v-btn>
      </j-tooltip>
    </v-row>

  </j-tray-plugin>
</template>
