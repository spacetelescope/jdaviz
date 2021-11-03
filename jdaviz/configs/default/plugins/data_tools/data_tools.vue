<template>
  <v-toolbar-items>
    <v-dialog v-model="dialog" height="400" width="600">
      <template v-slot:activator="{ on }">
        <v-btn tile depressed v-on="on" color="turquoise">
          Import
          <v-icon right>mdi-plus</v-icon>
        </v-btn>
      </template>

      <v-card>

        <v-card-title class="headline" color="primary" primary-title>Import Data</v-card-title>

        <v-card-text>
          Single click to select directory. Select and click "IMPORT" to open a file.
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
