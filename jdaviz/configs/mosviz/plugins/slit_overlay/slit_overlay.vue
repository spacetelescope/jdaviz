<template>
  <j-tray-plugin>
    <v-row>
      <j-docs-link :link="'https://jdaviz.readthedocs.io/en/'+vdocs+'/'+config+'/plugins.html#slit-overlay'">Add a slit to the image viewer</j-docs-link>
    </v-row>

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
