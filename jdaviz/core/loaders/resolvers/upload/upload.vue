<template>
    <j-loader
        title="Upload Local File"
        :target_items="target_items"
        :target_selected.sync="target_selected"
        :format_items_spinner="format_items_spinner"
        :format_items="format_items"
        :format_selected.sync="format_selected"
        :importer_widget="importer_widget"
        :api_hints_enabled="api_hints_enabled"
        :import_spinner="import_spinner"
        @import-clicked="import_clicked"
    >
        <jupyter-widget :widget="file_drop_widget"></jupyter-widget>
        <v-progress-linear v-if="progress !== 100" :value="progress"></v-progress-linear>
    </j-loader>
</template>