<template>
  <v-card flat>
    <v-card-title class="headline" color="primary" primary-title>{{title}}</v-card-title>
    <v-card-text>
        <v-container>
            <slot/>
        </v-container>
        <div style="display: grid"> <!-- overlay container -->
            <div style="grid-area: 1/1">
                <v-row justify="end" class="row-no-outside-padding" style="margin-bottom: -6px !important">
                  <div v-for="target_item in target_items">
                    <j-tooltip v-if="target_item.label !== 'Any'" :tooltipcontent="'Show only '+target_item.label+' formats'">
                      <v-btn
                        tile
                        :elevation=0
                        x-small
                        dense 
                        :color="target_selected === target_item.label ? 'turquoise' : 'transparent'"
                        :dark="target_selected === target_item.label"
                        style="padding-left: 8px; padding-right: 6px;"
                        @click="() => {if (target_selected === target_item.label) {$emit('update:target_selected', 'Any')} else {$emit('update:target_selected', target_item.label)}}"
                      >
                        {{ target_item.label }}
                      </v-btn>
                    </j-tooltip>
                  </div>
                </v-row>

                <plugin-select
                    :show_if_single_entry="true"
                    :items="format_items.map(i => i.label)"
                    :selected.sync="format_selected"
                    label="Format"
                    api_hint="loader.format ="
                    :api_hints_enabled="api_hints_enabled"
                    hint="Choose input format"
                />
                <v-row v-if="format_selected.length">
                    <jupyter-widget :widget="importer_widget"></jupyter-widget>
                </v-row>
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
          :results_isolated_to_plugin="false"
          :api_hints_enabled="false"
          @click="$emit('cancel-clicked')">
          Cancel
        </plugin-action-button>
        <plugin-action-button 
          :spinner="import_spinner"
          :disabled="!format_selected.length"
          :results_isolated_to_plugin="false"
          :api_hints_enabled="api_hints_enabled"
          @click="$emit('import-clicked')">
          {{ api_hints_enabled ?
            'loader.importer()'
            :
            'Import'
          }}
        </plugin-action-button>
    </v-card-actions>
  </v-card>
</template>

<script>
module.exports = {
  props: ['title',
          'target_items', 'target_selected',
          'format_items_spinner', 'format_items', 'format_selected',
          'importer_widget', 'import_spinner',
          'api_hints_enabled'],
}
</script>
