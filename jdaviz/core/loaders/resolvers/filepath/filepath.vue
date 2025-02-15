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
                </v-col>
                </v-row>



                <div style="display: grid"> <!-- overlay container -->
                    <div style="grid-area: 1/1">
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



            </v-container>

        </v-card-text>
    </v-card>
</template>
  