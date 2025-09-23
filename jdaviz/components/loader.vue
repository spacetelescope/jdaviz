<template>
  <v-card flat>
    <v-card-title v-if="!server_is_remote" class="headline" color="primary" primary-title style="display: block; width: 100%">
      {{title}}
      <span style="float: right">
        <j-plugin-popout :popout_button="popout_button"></j-plugin-popout>
      </span>
    </v-card-title>
    <v-card-text>
        <v-container v-if="!server_is_remote">
          <slot/>
        </v-container>

        <!-- products list selection -->
        <div v-if="parsed_input_is_products_list">
          <j-plugin-section-header>Products List</j-plugin-section-header>
          <plugin-switch
            label="Treat Table as Products List"
            :value.sync="treat_table_as_products_list"
            api_hint="ldr.treat_table_as_products_list ="
            :api_hints_enabled="api_hints_enabled"
            style="margin-bottom: 12px"
          ></plugin-switch>

          <div v-if="treat_table_as_products_list">
            <v-row>
              <v-expansion-panels popout>
                <v-expansion-panel>
                  <v-expansion-panel-header v-slot="{ open }">
                    <span style="padding: 6px">Product Download Options</span>
                  </v-expansion-panel-header>
                  <v-expansion-panel-content class="plugin-expansion-panel-content">
                    <v-content>
                      <v-row v-if="products_url_scheme !== 's3'">
                        <v-text-field
                          v-model.number='products_timeout'
                          type="number"
                          style="padding: 0px 8px"
                          suffix="s"
                          :label="api_hints_enabled ? 'ldr.products_timeout =' : 'Timeout (s)'"
                          :class="api_hints_enabled ? 'api-hint' : null"
                        ></v-text-field>
                      </v-row>

                      <plugin-switch
                        v-if="products_url_scheme !== 's3'"
                        :value.sync="products_cache"
                        label="Cache File"
                        api_hint="ldr.products_cache = "
                        :api_hints_enabled="api_hints_enabled"
                        hint="Whether to attempt to read from the cache if this same URL has been previously fetched."
                      ></plugin-switch>
                    </v-content>
                  </v-expansion-panel-content>
                </v-expansion-panel>
              </v-expansion-panels>
            </v-row>

            <jupyter-widget v-if="treat_table_as_products_list" :widget="table_widget"></jupyter-widget>
          </div>

        <!-- format (parser/importer) selection and UI -->
        <j-plugin-section-header>Importer</j-plugin-section-header>
        <div style="display: grid"> <!-- overlay container -->
            <div style="grid-area: 1/1">
                <v-container style="padding-right: 28px">
                  <v-row v-if="target_items.length >= 2" style="padding-right: 12px">
                    <plugin-select-filter
                      :items="target_items"
                      :selected.sync="target_selected"
                      @update:selected="$emit('update:target_selected', $event)"
                      tooltip_suffix="compatible formats"
                      api_hint="ldr.target ="
                      :api_hints_enabled="api_hints_enabled"
                    />
                  </v-row>

                  <v-row v-if="format_items.length == 0 && valid_import_formats">
                      <v-alert type="warning" style="margin-left: -12px; margin-right: -12px; width: 100%">
                          No compatible importer found. Supported input types include: {{ valid_import_formats }}.
                      </v-alert>
                  </v-row>
                  <v-row v-if="format_items.length === 1" style="margin-top: 16px">
                      <span v-if="api_hints_enabled" class="api-hint" style="margin-right: 6px">ldr.format = '{{ format_selected }}'</span>
                      <span v-else>Format: {{ format_selected }}</span>
                  </v-row>
                  <plugin-select
                      v-if="format_items.length >= 2"
                      :show_if_single_entry="false"
                      :items="format_items.map(i => i.label)"
                      :selected.sync="format_selected"
                      @update:selected="$emit('update:format_selected', $event)"
                      label="Format"
                      api_hint="ldr.format ="
                      :api_hints_enabled="api_hints_enabled"
                      hint="Choose input format"
                  ></plugin-select>
                  <v-row v-if="format_selected.length > 0" style="margin-top: 16px">
                     <jupyter-widget :widget="importer_widget"></jupyter-widget>
                  </v-row>
                </v-container>
            </div>
            <div v-if="format_items_spinner"
                class="text-center"
                style="grid-area: 1/1;
                        z-index:2;
                        margin-left: -24px;
                        margin-right: -24px;
                        padding-top: 24px;
                        background-color: rgb(0 0 0 / 20%)">
                <v-progress-circular
                    indeterminate
                    color="spinner"
                    size="50"
                    width="6"
                />
            </div>
        </div> <!-- overlay container -->
    </v-card-text>
  </v-card>
</template>

<script>
module.exports = {
  props: ['title', 'popout_button', 'parse_input_spinner',
          'parsed_input_is_products_list', 'treat_table_as_products_list',
          'products_url_scheme', 'products_cache', 'products_timeout',
          'table_widget',
          'target_items', 'target_selected',
          'format_items_spinner', 'format_items', 'format_selected',
          'importer_widget', 'server_is_remote',
          'api_hints_enabled', 'valid_import_formats'],
}
</script>