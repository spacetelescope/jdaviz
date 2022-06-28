<template>
  <j-tray-plugin
    description='Re-link images by WCS or pixels.'
    :link="'https://jdaviz.readthedocs.io/en/'+vdocs+'/'+config+'/plugins.html#link-control'"
    :popout_button="popout_button">

    <v-row>
      <v-radio-group 
        label="Link type"
        hint="Type of linking to be done."
        v-model="link_type"
        persistent-hint
        row>
        <v-radio
          v-for="item in link_types"
          :key="item"
          :label="item"
          :value="item"
        ></v-radio>
       </v-radio-group>
    </v-row>

    <v-row v-if="false">
      <v-switch
        label="Fallback on Pixels"
        hint="If WCS linking fails, fallback to linking by pixels."
        v-model="wcs_use_fallback"
        persistent-hint>
      </v-switch>
    </v-row>

    <v-row v-if="link_type == 'WCS'">
      <v-switch
        label="Fast approximation"
        hint="Use fast approximation for image alignment if possible (accurate to <1 pixel)."
        v-model="wcs_use_affine"
        persistent-hint>
      </v-switch>
    </v-row>

    <v-row justify="end">
      <j-tooltip tipid='plugin-link-apply'>
        <v-btn color="accent" text @click="do_link">Link</v-btn>
      </j-tooltip>
    </v-row>
  </j-tray-plugin>
</template>

<style>

/* addresses https://github.com/pllim/jdaviz/pull/3#issuecomment-926820530 */
div[role=radiogroup] > legend {
  width: 100%;
}

</style>
