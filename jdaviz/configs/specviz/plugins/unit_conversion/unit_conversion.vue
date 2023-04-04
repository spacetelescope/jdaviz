<template>
  <!-- To re-enable plugin, use :disabled_msg="disabled_msg" -->
  <j-tray-plugin
    description='Convert the spectral flux density and spectral axis units.'
    :link="'https://jdaviz.readthedocs.io/en/'+vdocs+'/'+config+'/plugins.html#unit-conversion'"
    :disabled_msg="disabled_msg"
    :popout_button="popout_button">

    <v-row>
      <v-select
        :menu-props="{ left: true }"
        attach
        :items="spectral_unit_items.map(i => i.label)"
        v-model="spectral_unit_selected"
        label="Spectral Unit"
        hint="Global display unit for spectral axis."
        persistent-hint
      ></v-select>
    </v-row>

    <v-row>
      <v-select
        :menu-props="{ left: true }"
        attach
        :items="flux_unit_items.map(i => i.label)"
        v-model="flux_unit_selected"
        label="Flux Unit"
        hint="Global display unit for flux."
        persistent-hint
      ></v-select>
    </v-row>
  </j-tray-plugin>
</template>
