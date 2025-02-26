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
        :import_spinner="import_spinner"
        @import-clicked="import_clicked"
    >
        <v-row>
            Select a file with data you want to load into this instance of Jdaviz
            and click "IMPORT".
            Note that single clicks navigate into directories.
        </v-row>
        <v-row>
          <g-file-import id="file-uploader"></g-file-import>
        </v-row>
    </j-loader>
</template>