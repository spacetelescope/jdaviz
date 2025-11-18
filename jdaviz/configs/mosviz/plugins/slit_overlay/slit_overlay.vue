<template>
  <j-tray-plugin
    :description="docs_description"
    :link="docs_link || 'https://jdaviz.readthedocs.io/en/'+vdocs+'/'+config+'/plugins.html#slit-overlay'"
    :popout_button="popout_button"
    :api_hints_enabled.sync="api_hints_enabled"
    :scroll_to.sync="scroll_to">

    <v-row>
      <v-switch
        label="Visible"
        hint="Show slit in the image viewer."
        api_hint="plg.visible = "
        :api_hints_enabled="api_hints_enabled"
        v-model="visible"
        @click.native="change_visible"
        persistent-hint>
      </v-switch>
    </v-row>
  </j-tray-plugin>
</template>
