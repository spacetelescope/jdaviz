<template>
  <div style="position: relative; height: 100%;">
    <!-- Top sticky overlay -->
    <div v-if="spinner.length > 0" class="top-overlay">
      <div class="overlay-content">
        {{  spinner || "Loading..." }}
        <v-progress-linear
            color="#c75d2c"
            indeterminate
            height="6"
          ></v-progress-linear>
      </div>
    </div>

    <v-card flat>
      <v-card-title v-if="!server_is_remote" class="headline" color="primary" primary-title style="display: block; width: 100%">
        {{title}}
        <span style="float: right">
          <j-plugin-popout :popout_button="popout_button"></j-plugin-popout>
        </span>
      </v-card-title>
      <v-card-text>
        <v-container v-if="!server_is_remote" style="padding: 4px">
          <slot/>
        </v-container>

        <v-container>
          <v-alert v-if="image_data_loaded && is_wcs_linked !== undefined && treat_table_as_query && observation_table_populated && !is_wcs_linked"
                   type="warning" dense style="margin-bottom: 16px; margin-top: 8px">
            <v-row no-gutters align="center">
              <v-col>
                <strong>Images are not linked by WCS.</strong> Link images to view footprints properly.
              </v-col>
              <v-col cols="auto" style="margin-left: 8px;">
                <v-btn small color="primary" @click="$emit('link-by-wcs')">
                  Link by WCS
                </v-btn>
              </v-col>
            </v-row>
          </v-alert>

          <j-custom-toolbar-toggle
            v-if="footprint_select_icon && treat_table_as_query && is_wcs_linked && observation_table_populated"
            :enabled="custom_toolbar_enabled"
            text="footprint selection tools"
            @toggle-custom-toolbar="$emit('toggle-custom-toolbar')"
            style="margin-bottom: 16px"
          >
            <img class="invert-if-dark" :src="footprint_select_icon" width="20"/>
          </j-custom-toolbar-toggle>

          <!-- observation/file table -->
          <div v-if="parsed_input_is_query">
            <j-plugin-section-header>Query Results</j-plugin-section-header>
            <plugin-switch
              label="Treat Table as Query"
              :value.sync="treat_table_as_query"
              @update:value="$emit('update:treat_table_as_query', $event)"
              api_hint="ldr.treat_table_as_query ="
              :api_hints_enabled="api_hints_enabled"
              style="margin-bottom: 12px"
            ></plugin-switch>

            <div v-if="treat_table_as_query && observation_table_populated">
              <span class="table-title">Observations</span>
              <span v-if="api_hints_enabled" class="api-hint">ldr.observation_table</span>

              <jupyter-widget v-if="treat_table_as_query" :widget="observation_table"></jupyter-widget>
            </div>
            <div v-if="treat_table_as_query && file_table_populated">
              <span class="table-title">Files</span>
              <v-row>
                <v-expansion-panels popout>
                  <v-expansion-panel>
                    <v-expansion-panel-header v-slot="{ open }">
                      <span style="padding: 6px">File Download Options</span>
                    </v-expansion-panel-header>
                    <v-expansion-panel-content class="plugin-expansion-panel-content">
                      <v-content>
                        <v-row>
                          <v-text-field
                            v-model.number='file_timeout'
                            type="number"
                            style="padding: 0px 8px"
                            suffix="s"
                            :label="api_hints_enabled ? 'ldr.file_timeout =' : 'Timeout (s)'"
                            :class="api_hints_enabled ? 'api-hint' : null"
                          ></v-text-field>
                        </v-row>

                        <plugin-switch
                          :value.sync="file_cache"
                          label="Cache File"
                          api_hint="ldr.file_cache = "
                          :api_hints_enabled="api_hints_enabled"
                          hint="Whether to attempt to read from the cache if this same URL has been previously fetched."
                        ></plugin-switch>
                      </v-content>
                    </v-expansion-panel-content>
                  </v-expansion-panel>
                </v-expansion-panels>
              </v-row>

              <span v-if="api_hints_enabled" class="api-hint">ldr.file_table</span>
              <jupyter-widget v-if="treat_table_as_query" :widget="file_table"></jupyter-widget>
            </div>
          </div>
          <!-- end observation/file table -->

          <!-- format (parser/importer) selection and UI -->
          <j-plugin-section-header>Importer</j-plugin-section-header>

          <v-row v-if="target_items.length >= 2" style="padding-right: 16px">
            <plugin-select-filter
              :items="target_items"
              :selected.sync="target_selected"
              @update:selected="$emit('update:target_selected', $event)"
              tooltip_suffix="compatible formats"
              api_hint="ldr.target ="
              :api_hints_enabled="api_hints_enabled"
            />
          </v-row>

          <v-row v-if="parsed_input_is_empty">
            <v-alert type="warning" style="margin-right: -12px; width: 100%">
                Input is empty.
            </v-alert>
          </v-row>
          <v-row v-else-if="format_items.length == 0 && valid_import_formats">
              <v-alert type="warning" style="margin-right: -12px; width: 100%">
                  No compatible importer found. Supported input types include: {{ valid_import_formats }}.
              </v-alert>
          </v-row>
          <v-row v-if="format_items.length === 1" style="margin-top: 16px; margin-left: 8px">
              <span v-if="api_hints_enabled" class="api-hint" style="margin-right: 6px">ldr.format = '{{ format_selected }}'</span>
              <span v-else><b>Format:</b> {{ format_selected }}</span>
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
          <div v-if="format_selected.length > 0" style="margin-top: 16px; margin-left: -12px; margin-right: -12px">
              <jupyter-widget :widget="importer_widget"></jupyter-widget>
          </div>
        </v-container>
      </v-card-text>
    </v-card>
  </div>
</template>

<script>
module.exports = {
  props: ['title', 'popout_button', 'spinner',
          'parsed_input_is_empty', 'parsed_input_is_query', 'treat_table_as_query',
          'observation_table', 'observation_table_populated',
          'file_table', 'file_table_populated',
          'file_cache', 'file_timeout',
          'target_items', 'target_selected',
          'format_items', 'format_selected',
          'importer_widget', 'server_is_remote',
          'api_hints_enabled', 'valid_import_formats',
          'is_wcs_linked', 'footprint_select_icon', 'custom_toolbar_enabled','image_data_loaded'],

}
</script>

<style scoped>
  .top-overlay {
    position: sticky;
    top: 0;
    left: 0;
    right: 0;
    background: rgba(255, 255, 255, 0.95);
    border-bottom: 1px solid #e0e0e0;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
    z-index: 10;
    padding: 0px;
  }

  .overlay-content {
    text-align: center;
    color: #666;
    font-size: 14px;
  }

  .table-title {
    margin-top: 24px;
    margin-left: 20px;
    margin-right: 20px;
    display: block;
    text-align: center;
    overflow: hidden;
    white-space: nowrap;
    text-transform: uppercase;
    color: gray;
    font-weight: 500;
  }

  .plugin-table-component {
    margin: 0px
  }
</style>