<template>
  <!-- To re-enable plugin, use :disabled_msg="disabled_msg" -->
  <j-tray-plugin
    :description="docs_description || 'Convert the spectral flux density and spectral axis units.'"
    :link="docs_link || 'https://jdaviz.readthedocs.io/en/'+vdocs+'/'+config+'/plugins.html#unit-conversion'"
    :disabled_msg="disabled_msg"
    :popout_button="popout_button"
    :scroll_to.sync="scroll_to">

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

    <v-row  v-if="config == 'cubeviz' && show_translator">
      <v-select
        :menu-props="{ left: true }"
        attach
        :items="flux_or_sb_items.map(i => i.label)"
        v-model="flux_or_sb_selected"
        label="Flux or Surface Brightness"
        hint="Select between Flux or Surface Brightness physical type for y-axis."
        persistent-hint
        :disabled="!can_translate"
      ></v-select>
      <span v-if="!can_translate">Translation is not available due to current unit selection.</span>
    </v-row>

    <v-row>
      <v-select
        :menu-props="{ left: true }"
        attach
        :items="flux_unit_items.map(i => i.label)"
        v-model="flux_unit_selected"
        label="Flux Unit"
        hint="Global display unit for y-axis axis."
        persistent-hint
      ></v-select>
    </v-row>

    <v-row>
      <v-select
        :menu-props="{ left: true }"
        attach
        :items="sb_unit_items.map(i => i.label)"
        v-model="sb_unit_selected"
        label="Surface Brightness Unit"
        hint="Global display unit for y-axis axis."
        persistent-hint
        :disabled="!can_translate"
      ></v-select>
      <span v-if="!can_translate">Translation is not available due to current unit selection.</span>
    </v-row>

  </j-tray-plugin>
</template>
