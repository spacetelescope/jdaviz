<template>
  <v-toolbar-items>
    <v-dialog v-model="dialog" height="400" width="600">
      <template v-slot:activator="{ on }">
        <v-btn tile depressed v-on="on" color="turquoise">
          Import Data
        </v-btn>
      </template>

      <v-card>

        <v-card-title class="headline" color="primary" primary-title>Import Data</v-card-title>

        <v-card-text>
          Select a file with data you want to load into this instance of Jdaviz
          and click "IMPORT". Imported data can be shown in any compatible
          viewer{{ config == 'cubeviz' ? ', though only one data cube may be loaded per instance' : ''}}.
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

        <v-card-actions>
          <div class="flex-grow-1"></div>
          <v-btn color="primary" text @click="dialog = false">Cancel</v-btn>
          <v-btn color="primary" text @click="load_data" :disabled="!valid_path">Import</v-btn>
        </v-card-actions>

      </v-card>
    </v-dialog>
  </v-toolbar-items>
</template>
