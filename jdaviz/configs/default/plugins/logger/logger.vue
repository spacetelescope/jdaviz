<template>
  <j-tray-plugin
    :config="config"
    plugin_key="Logger"
    v-model:api_hints_enabled="api_hints_enabled"
    :description="docs_description"
    :popout_button="popout_button"
    v-model:scroll_to="scroll_to">

    <plugin-select
      :items="popup_verbosity_items.map(i => i.label)"
      v-model:selected="popup_verbosity_selected"
      label="Popup Verbosity Level"
      api_hint="plg.popup_verbosity ="
      :api_hints_enabled="api_hints_enabled"
      hint="Minimum verbosity level to show a popup message."
    ></plugin-select>

    <plugin-select
      :items="history_verbosity_items.map(i => i.label)"
      v-model:selected="history_verbosity_selected"
      label="History Verbosity Level"
      api_hint="plg.history_verbosity ="
      :api_hints_enabled="api_hints_enabled"
      hint="Minimum verbosity level to show in the log below."
    ></plugin-select>

    <j-flex-row justify="end">
      <plugin-action-button
        :disabled="history.length == 0"
        :results_isolated_to_plugin="true"
        :api_hints_enabled="api_hints_enabled"

        @click="clear_history">
          <v-icon>mdi-notification-clear-all</v-icon>
          {{ api_hints_enabled ?
            'plg.clear_history()'
            :
            'Clear History'
          }}
      </plugin-action-button>
    </j-flex-row>

    <v-alert v-if="history.length === 0" density="compact" type="info">No logger messages</v-alert>
    <j-flex-row density="compact" @click="(e) => {e.stopImmediatePropagation()}"
        v-for="(hist, index) in history.slice().reverse()"
        style="margin: 6px 0px 0px 0px; max-width: 100%; overflow: hidden"
    >
      <v-alert
        density="compact"
        style="width: 100%; overflow: scroll; white-space: wrap; word-wrap: break-word;"
        :type="hist.color">
          <j-flex-row v-if="api_hints_enabled">
            <span class="api-hint" style="margin-left: 12px">
              plg.history[{{history.length - 1 - index}}]
            </span>
          </j-flex-row>
          [{{hist.time}}]: {{hist.text}}
      </v-alert>
    </j-flex-row>

  </j-tray-plugin>
</template>
