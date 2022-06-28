<template>
  <j-tray-plugin
    description='Add a slit to the image viewer.'
    :link="'https://jdaviz.readthedocs.io/en/'+vdocs+'/'+config+'/plugins.html#slit-overlay'"
    :popout_button="popout_button">

    <v-row>
      <v-switch
        label="Visible"
        hint="Show slit in the image viewer."
        v-model="visible"
        @click.native="change_visible"
        persistent-hint>
      </v-switch>
    </v-row>
  </j-tray-plugin>
</template>
