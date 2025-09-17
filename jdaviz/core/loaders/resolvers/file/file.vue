<template>
    <j-loader
        title="Load Local File"
        :popout_button="popout_button"
        :target_items="target_items"
        :target_selected.sync="target_selected"
        :format_items_spinner="format_items_spinner"
        :format_items="format_items"
        :format_selected.sync="format_selected"
        :importer_widget="importer_widget"
        :api_hints_enabled="api_hints_enabled"
        :valid_import_formats="valid_import_formats"
        :server_is_remote="server_is_remote"
    >
        <v-row>
            Select a file with data you want to load into this instance of Jdaviz.
        </v-row>
        <v-row v-if="api_hints_enabled">
            <span class="api-hint">
                ldr.filepath = '{{ filepath }}'
            </span>
        </v-row>
        <jupyter-widget :widget="file_chooser_widget"></jupyter-widget>
    </j-loader>
</template>