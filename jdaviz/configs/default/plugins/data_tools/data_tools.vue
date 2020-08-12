<template>
  <v-toolbar-items>
    <v-dialog v-model="dialog" width="500" persistent>
      <template v-slot:activator="{ on }">
        <v-btn tile depressed v-on="on" color="accent">
          Import
          <v-icon right>mdi-plus</v-icon>
        </v-btn>
      </template>

      <v-card>
        <v-card-title class="headline" color="primary" primary-title>Import Data</v-card-title>

        <v-card-text>
          <v-container>
            <v-row>
              <v-col>
                <!-- <v-file-input v-model="files" label="File input"></v-file-input> -->
                <v-text-field
                  label="File Path"
                  placeholder="/path/to/data/file"
                  v-model="file_path"
                  :error-messages="error_message"
                ></v-text-field>
              </v-col>
            </v-row>
          </v-container>
        </v-card-text>
        <!-- <v-divider></v-divider> -->

        <v-card-actions>
          <div class="flex-grow-1"></div>
          <v-btn color="primary" text @click="dialog = false">Cancel</v-btn>
          <v-btn color="primary" text @click="load_data" :disabled="!valid_path">Import</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
    <v-tooltip bottom>
      <template v-slot:activator="{ on }">
        <v-btn disabled v-on="on" icon tile>
          <v-icon>mdi-format-superscript</v-icon>
        </v-btn>
      </template>
      <span>Arithmetic Editor</span>
    </v-tooltip>
    <v-tooltip bottom>
      <template v-slot:activator="{ on }">
        <v-btn disabled v-on="on" icon tile>
          <v-icon>mdi-export</v-icon>
        </v-btn>
      </template>
      <span>Export Data</span>
    </v-tooltip>
    <v-tooltip bottom>
      <template v-slot:activator="{ on }">
        <v-btn disabled v-on="on" icon tile>
          <v-icon>mdi-delete</v-icon>
        </v-btn>
      </template>
      <span>Delete Data</span>
    </v-tooltip>
    <!-- <v-divider vertical></v-divider> -->
  </v-toolbar-items>
</template>