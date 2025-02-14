<template>
    <v-card>
        <v-card-title class="headline" color="primary" primary-title>Import Data</v-card-title>

        <v-card-text>
            Select a file with data you want to load into this instance of Jdaviz
            and click "IMPORT".
            Note that single clicks navigate into directories.
            <v-container>
                <v-row>
                <v-col>
                    <g-file-import id="file-uploader"></g-file-import>
                    <span style="color: red;">{{ error_message }}</span>
                </v-col>
                </v-row>


                <plugin-select
                    :show_if_single_entry="true"
                    :items="format_items.map(i => i.label)"
                    :selected.sync="format_selected"
                    label="Format"
                    api_hint="loader.format ="
                    :api_hints_enabled="false"
                    hint="Choose input format"
                />
                <div v-if="format_selected.length">
                    <p>Importer Options:</p>
                    <jupyter-widget :widget="importer_widget"></jupyter-widget>
                </div>
            </v-container>

        </v-card-text>
    </v-card>
</template>
  