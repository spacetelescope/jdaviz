<template>
  <j-loader
    title="Download from URL"
    :popout_button="popout_button"
    :target_items="target_items"
    :target_selected.sync="target_selected"
    :format_items_spinner="format_items_spinner"
    :format_items="format_items"
    :format_selected.sync="format_selected"
    :importer_widget="importer_widget"
    :api_hints_enabled="api_hints_enabled"
  >
    <v-row style="margin-bottom: 24px">
      <v-text-field
        v-model='url'
        prepend-icon='mdi-link-box'
        style="padding: 0px 8px"
        :label="api_hints_enabled ? 'ldr.url =' : ''"
        :class="api_hints_enabled ? 'api-hint' : null"
      ></v-text-field>
    </v-row>

    <v-row v-if="url_scheme !== 's3'">
      <v-text-field
        v-model.number='timeout'
        type="number"
        style="padding: 0px 8px"
        suffix="s"
        :label="api_hints_enabled ? 'ldr.timeout =' : 'Timeout (s)'"
        :class="api_hints_enabled ? 'api-hint' : null"
      ></v-text-field>
    </v-row>

    <plugin-switch
      v-if="url_scheme !== 's3'"
      :value.sync="cache"
      label="Cache File"
      api_hint="ldr.cache = "
      :api_hints_enabled="api_hints_enabled"
      hint="Whether to attempt to read from the cache if this same URL has been previously fetched."
    />
  </j-loader>
</template>