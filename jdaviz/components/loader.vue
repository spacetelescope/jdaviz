<template>
  <v-card flat>
    <v-card-title class="headline" color="primary" primary-title>{{title}}</v-card-title>
    <v-card-text>
        <v-container>
            <slot/>
        </v-container>
        <div style="display: grid"> <!-- overlay container -->
            <div style="grid-area: 1/1">
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
        <v-btn
            color="primary"
            :disabled="!format_selected.length"
            @click="alert('IMPORT')"
        >
            Import
        </v-btn>
    </v-card-actions>
  </v-card>
</template>

<script>
module.exports = {
  props: ['title', 'format_items_spinner', 'format_items', 'format_selected', 'importer_widget', 'api_hints_enabled'],
}
</script>
