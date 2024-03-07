<template>
  <v-alert v-if="previews_temp_disabled && show_live_preview" type='warning' style="margin-left: -12px; margin-right: -12px">
    Live-updating is temporarily disabled (last update took {{previews_last_time}}s)
    <v-row justify='center'>
      <j-tooltip tooltipcontent='hide live preview (can be re-enabled from the settings section in the plugin).' span_style="width: 100%">
        <v-btn style='width: 100%' @click="() => {$emit('update:show_live_preview', false); $emit('disable_previews')}">
          disable previews
        </v-btn>
      </j-tooltip>
    </v-row>
    <v-row justify='center'>
      <j-tooltip tooltipcontent='manually update live-previews based on current plugin inputs.' span_style="width: 100%">
        <v-btn style='width: 100%' @click="$emit('update:previews_temp_disabled', false)">
          update preview
        </v-btn>
      </j-tooltip>
    </v-row>
  </v-alert>
</template>

<script>
module.exports = {
  props: ['previews_temp_disabled', 'show_live_preview', 'previews_last_time']
};
</script>
