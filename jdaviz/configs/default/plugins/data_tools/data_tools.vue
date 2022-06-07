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
                <span style="color: red">{{ error_message }}</span>
              </v-col>
            </v-row>
          </v-container>
        </v-card-text>

        <v-card-actions>
          <div class="flex-grow-1"></div>
          <v-btn color="primary" text @click="dialog = false">Cancel</v-btn>
          <v-tooltip bottom>
            <template v-slot:activator="{ on }">
              <!-- wrap in a span to enable tooltip when button disabled -->
              <span v-on="on">
                <v-btn
                  color="primary"
                  text
                  @click="load_directory"
                  :disabled="!Boolean(directory)"
                  >Import directory</v-btn
                >
              </span>
            </template>
            <div>
              <span v-if="Boolean(directory)">Import {{ directory }}</span>
              <span v-else>Select or enter a directory before importing</span>
            </div>
          </v-tooltip>
          <v-tooltip bottom>
            <template v-slot:activator="{ on }">
              <span v-on="on">
                <v-btn
                  color="primary"
                  text
                  @click="load_file"
                  :disabled="!Boolean(file)"
                  >Import file</v-btn
                >
              </span>
            </template>
            <span v-if="Boolean(file)">Import {{ file }}</span>
            <span v-else>Select a file before importing, or double click a file.</span>
          </v-tooltip>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-toolbar-items>
</template>
