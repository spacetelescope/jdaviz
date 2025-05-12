<template>
  <j-tray-plugin
    :config="config"
    plugin_key="Logger"
    :api_hints_enabled.sync="api_hints_enabled"
    :description="docs_description"
    :popout_button="popout_button"
    :scroll_to.sync="scroll_to">


    <span v-if="api_hints_enabled" class="api-hint">plg.history</span>
    <v-alert v-if="history.length === 0" dense type="info">No logger messages</v-alert>
    <v-row
        dense
        @click="(e) => {e.stopImmediatePropagation()}"
        v-for="hist in history.slice().reverse()"
        style="margin: 6px 0px 0px 0px; max-width: 100%; overflow: hidden"
    >
      <v-alert
        dense
        style="width: 100%; overflow: scroll; white-space: wrap; word-wrap: break-word;"
        :type="hist.color">
          [{{hist.time}}]: {{hist.text}}
      </v-alert>
    </v-row>

  </j-tray-plugin>
</template>
