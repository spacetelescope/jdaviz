<template>
  <j-loader
    :title="title"
    :popout_button="popout_button"
    :spinner="spinner"
    :parsed_input_is_resolvable="parsed_input_is_resolvable"
    :parsed_input_is_query="parsed_input_is_query"
    v-model:treat_table_as_query="treat_table_as_query"
    :observation_table="observation_table"
    :observation_table_populated="observation_table_populated"
    :file_table="file_table"
    :file_table_populated="file_table_populated"
    :file_cache="file_cache"
    :file_timeout="file_timeout"
    :target_items="target_items"
    v-model:target_selected="target_selected"
    :format_items="format_items"
    v-model:format_selected="format_selected"
    :importer_widget="importer_widget"
    :api_hints_enabled="api_hints_enabled"
    :hide_resolver="hide_resolver"
    :hide_resolver_inputs="hide_resolver_inputs"
    :is_wcs_linked="is_wcs_linked"
    :image_data_loaded="image_data_loaded"
    :footprint_select_icon="footprint_select_icon"
    :custom_toolbar_enabled="custom_toolbar_enabled"
  >
    <div v-if="!hide_resolver_inputs">
      <j-flex-row style="margin-bottom: 24px">
        <v-text-field
          v-model='url'
          prepend-icon='mdi-link-box'
          style="padding: 0px 8px"
          :label="api_hints_enabled ? 'ldr.url =' : ''"
          :class="api_hints_enabled ? 'api-hint' : null"
          :error-messages="parsed_input_is_resolvable ? [parsed_input_is_resolvable] : []"
        ></v-text-field>
      </j-flex-row>

      <j-flex-row v-if="url_not_whitelisted">
        <v-alert type="warning" style="margin-right: -12px; width: 100%">
          The URL must start with: {{ url_prefix_whitelist.join(', ') }}
        </v-alert>
      </j-flex-row>

      <j-flex-row v-if="url_scheme !== 's3'">
        <v-text-field
          v-model.number='timeout'
          type="number"
          style="padding: 0px 8px"
          suffix="s"
          :label="api_hints_enabled ? 'ldr.timeout =' : 'Timeout (s)'"
          :class="api_hints_enabled ? 'api-hint' : null"
        ></v-text-field>
      </j-flex-row>

      <plugin-switch
        v-if="url_scheme !== 's3'"
        v-model:value="cache"
        label="Cache File"
        api_hint="ldr.cache = "
        :api_hints_enabled="api_hints_enabled"
        hint="Whether to attempt to read from the cache if this same URL has been previously fetched."
      ></plugin-switch>
    </div>
  </j-loader>
</template>
