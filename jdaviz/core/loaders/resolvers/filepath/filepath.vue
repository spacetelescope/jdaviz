<template>
    <j-loader
        title="Import Data"
        :format_items_spinner="format_items_spinner"
        :format_items="format_items"
        :format_selected.sync="format_selected"
        :importer_widget="importer_widget"
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