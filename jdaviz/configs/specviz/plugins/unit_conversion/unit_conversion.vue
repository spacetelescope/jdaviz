<template>
  <j-tray-plugin
    :config="config"
    plugin_key="Unit Conversion"
    :api_hints_enabled.sync="api_hints_enabled"
    :description="docs_description"
    :link="docs_link || 'https://jdaviz.readthedocs.io/en/'+vdocs+'/'+config+'/plugins.html#unit-conversion'"
    :disabled_msg="disabled_msg"
    :popout_button="popout_button"
    :scroll_to.sync="scroll_to">

    <plugin-select
      v-if="has_spectral"
      :items="spectral_unit_items.map(i => i.label)"
      :selected.sync="spectral_unit_selected"
      label="Spectral Unit"
      api_hint="plg.spectral_unit ="
      :api_hints_enabled="api_hints_enabled"
      hint="Global display unit for spectral axis."
    />

    <plugin-select
      v-if="has_time"
      :items="time_unit_items.map(i => i.label)"
      :selected.sync="time_unit_selected"
      label="Time Unit"
      api_hint="plg.time_unit ="
      :api_hints_enabled="api_hints_enabled"
      hint="Global display unit for time axis."
    />

    <plugin-select
      v-if="has_flux"
      :items="flux_unit_items.map(i => i.label)"
      :selected.sync="flux_unit_selected"
      label="Flux Unit"
      api_hint="plg.flux_unit ="
      :api_hints_enabled="api_hints_enabled"
      hint="Global display unit for flux axis."
    />

    <plugin-select
      v-if="has_angle"
      :items="angle_unit_items.map(i => i.label)"
      :selected.sync="angle_unit_selected"
      label="Angle Unit"
      api_hint="plg.angle_unit ="
      :api_hints_enabled="api_hints_enabled"
      hint="Solid angle unit."
    />

    <v-row v-if="has_sb">
      <v-text-field
        v-model="sb_unit_selected"
        :label="api_hints_enabled ? 'plg.sb_unit' : 'Surface Brightness Unit'"
        :class="api_hints_enabled ? 'api-hint' : null"
        hint="Global display unit for surface brightness axis."
        persistent-hint
        :disabled='true'
      ></v-text-field>
    </v-row>

    <div v-if="config == 'cubeviz'">
      <v-row>
        <v-divider></v-divider>
      </v-row>

      <plugin-select
        :items="spectral_y_type_items.map(i => i.label)"
        :selected.sync="spectral_y_type_selected"
        label="Spectral y-axis Type"
        api_hint="plg.spectral_y_type ="
        :api_hints_enabled="api_hints_enabled"
        hint="Select the y-axis physical type for the spectrum-viewer."
      />


      <v-alert type="warning" v-if="!pixar_sr_exists">
            PIXAR_SR FITS header keyword not found when parsing spectral cube.
            Flux/Surface Brightness will use default PIXAR_SR value of 1.
      </v-alert>
    </div>

  </j-tray-plugin>
</template>
