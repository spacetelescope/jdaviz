<template>
    <j-loader
        title="File Drop"
        :popout_button="popout_button"
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
        <v-row>
            Select a file from your local file system and send to jdaviz through the browser.
        </v-row>
        <v-alert v-if="api_hints_enabled" type="info">
            Use UI to select file (no API access available).
        </v-alert>
        <jupyter-widget :widget="file_drop_widget"></jupyter-widget>
        <v-progress-linear v-if="progress !== 100" :value="progress"></v-progress-linear>
        <v-alert v-if="nfiles > 1" type="warning">
            Multiple files dropped, only using first entry.
        </v-alert>

    </j-loader>
</template>