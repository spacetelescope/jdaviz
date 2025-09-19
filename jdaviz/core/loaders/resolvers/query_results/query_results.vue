<template>
  <j-loader
    title="Query Results (from API)"
    :popout_button="popout_button"
    :target_items="target_items"
    :target_selected.sync="target_selected"
    :format_items_spinner="format_items_spinner"
    :format_items="format_items"
    :format_selected.sync="format_selected"
    :importer_widget="importer_widget"
    :api_hints_enabled="api_hints_enabled"
  >
    <v-alert type="info">
        Access the user API in a notebook cell to import a table of online query results.
    </v-alert>

    <j-plugin-section-header>Download Options</j-plugin-section-header>
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

    <j-plugin-section-header>Query Results</j-plugin-section-header>
    <jupyter-widget :widget="table_widget"></jupyter-widget>

  </j-loader>
</template>