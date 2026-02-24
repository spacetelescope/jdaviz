<template>
  <j-tray-plugin
    :description="docs_description"
    :link="docs_link || 'https://jdaviz.readthedocs.io/en/'+vdocs+'/'+config+'/plugins.html#slit-overlay'"
    :popout_button="popout_button"
    v-model:api_hints_enabled="api_hints_enabled"
    v-model:scroll_to="scroll_to">

    <v-row>
      <plugin-switch
        v-model:value="visible"
        label="Visible"
        api_hint="plg.visible = "
        :api_hints_enabled="api_hints_enabled"
        hint="Show slit in the image viewer."
      />
    </v-row>
  </j-tray-plugin>
</template>
