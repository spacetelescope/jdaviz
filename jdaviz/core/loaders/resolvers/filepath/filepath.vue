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
        </v-container>
        </v-card-text>
    </v-card>
</template>
  