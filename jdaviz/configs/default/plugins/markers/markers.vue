<template>
  <j-tray-plugin
    description='Create and export markers.  Press "m" with the cursor over a viewer to log the mouseover information.  To change the selected layer, click the layer cycler in the mouseover information section of the app-level toolbar.'
    :link="'https://jdaviz.readthedocs.io/en/'+vdocs+'/'+config+'/plugins.html#markers'"
    :has_previews="has_previews"
    :plugin_active.sync="plugin_active"
    :persistent_previews.sync="persistent_previews"
    :popout_button="popout_button">

    <v-row v-if="!persistent_previews">
      <v-alert color="warning">Persistent live-preview must be enabled for logging via keypress to be active</v-alert>
    </v-row>

    <jupyter-widget :widget="table_widget"></jupyter-widget> 

  </j-tray-plugin>
</template>
