<template>
  <v-card flat>
    <v-card-title class="headline" color="primary" primary-title style="display: block; width: 100%">
      {{title}}
      <span style="float: right">
        <j-plugin-popout :popout_button="popout_button"></j-plugin-popout>
      </span>
    </v-card-title>
    <v-card-text>
        <v-container>
          <slot/>
        </v-container>
        <div style="display: grid"> <!-- overlay container -->
            <div style="grid-area: 1/1">
                <v-container style="padding-right: 28px">
                  <v-row v-if="target_items.length >= 2" style="padding-right: 12px">
                    <plugin-select-filter
                      :items="target_items"
                      :selected.sync="target_selected"
                      @update:selected="$emit('update:target_selected', $event)"
                      tooltip_suffix="formats"
                      api_hint="ldr.target ="
                      :api_hints_enabled="api_hints_enabled"
                    />
                  </v-row>  

                  <v-row v-if="format_items.length == 0">
                      <v-alert type="warning" style="margin-left: -12px; margin-right: -12px; width: 100%">
                          No matching importers found for input.
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
    <v-card-actions>
        <v-spacer></v-spacer>
        <plugin-action-button 
          :spinner="import_spinner"
          :disabled="!format_selected.length"
          :results_isolated_to_plugin="false"
          :api_hints_enabled="api_hints_enabled"
          @click="$emit('import-clicked')">
          {{ api_hints_enabled ?
            'ldr.importer()'
            :
            'Import'
          }}
        </plugin-action-button>
    </v-card-actions>
  </v-card>
</template>

<script>
module.exports = {
  props: ['title', 'popout_button',
          'target_items', 'target_selected',
          'format_items_spinner', 'format_items', 'format_selected',
          'importer_widget', 'import_spinner',
          'api_hints_enabled'],
}
</script>