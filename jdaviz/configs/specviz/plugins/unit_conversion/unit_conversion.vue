<template>
  <j-tray-plugin
    :config="config"
    plugin_key="Unit Conversion"
    :api_hints_enabled.sync="api_hints_enabled"
    :description="docs_description || 'Convert the units of displayed physical quantities.'"
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
        :label="api_hints_enabled ? 'plg.spectral_unit =' : 'Spectral Unit'"
        :class="api_hints_enabled ? 'api-hint' : null"
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
        :label="api_hints_enabled ? 'plg.flux_unit =' : 'Flux Unit'"
        :class="api_hints_enabled ? 'api-hint' : null"
        hint="Global display unit for flux axis."
        persistent-hint
      ></v-select>
    </v-row>

    <v-row>
      <v-select
        :menu-props="{ left: true }"
        attach
        :items="angle_unit_items.map(i => i.label)"
        v-model="angle_unit_selected"
        :label="api_hints_enabled ? 'plg.angle_unit =' : 'Solid Angle Unit'"
        :class="api_hints_enabled ? 'api-hint' : null"
        hint="Solid angle unit."
        persistent-hint

      ></v-select>
    </v-row>

    <v-row>
      <v-text-field
        v-model="sb_unit_selected"
        :label="api_hints_enabled ? 'plg.sb_unit' : 'Surface Brightness Unit'"
        :class="api_hints_enabled ? 'api-hint' : null"
        hint="Global display unit for surface brightness axis."
        persistent-hint
        :disabled='true'
      ></v-text-field>
    </v-row>

    <v-row v-if="config == 'cubeviz'">
      <v-divider></v-divider>
    </v-row>

    <v-row  v-if="config == 'cubeviz'">
      <v-select
        :menu-props="{ left: true }"
        attach
        :items="spectral_y_type_items.map(i => i.label)"
        v-model="spectral_y_type_selected"
        :label="api_hints_enabled ? 'plg.spectral_y_type =' : 'Spectral y-axis Type'"
        :class="api_hints_enabled ? 'api-hint' : null"
        hint="Select the y-axis physical type for the spectrum-viewer."
        persistent-hint
      ></v-select>
    </v-row>

    <v-alert type="warning" v-if="!pixar_sr_exists && config == 'cubeviz'">
          PIXAR_SR FITS header keyword not found when parsing spectral cube.
          Flux/Surface Brightness will use default PIXAR_SR value of 1.
    </v-alert>

  </j-tray-plugin>
</template>
