<template>
  <div>
    <span style="float: right">
        <a :href="'https://jdaviz.readthedocs.io/en/'+vdocs" target="__blank">
            <b>Learn More</b>
        </a>
        |
        <a :href="'https://spacetelescope.github.io/jdat_notebooks/'" target="__blank">
            <b>Notebooks</b>
        </a>
        |
        <a :href="'https://github.com/spacetelescope/jdaviz'" target="__blank">
            <b>GitHub</b>
        </a>
    </span>

    <h1>Welcome to jdaviz!</h1>
    
    <v-row>
        <v-text-field
            v-model="filepath"
            class="my-4"
            dark
            outlined
            label="File Path"
            :hint="hint"
            persistent-hint
            :loading="hint === 'Please wait. Identifying file...' ? '#C75109' : 'false' " 
        >
        </v-text-field>

        <v-dialog v-model="file_chooser_visible" height="400" width="600">
            <template v-slot:activator="{ on }">
            <v-btn
                v-on="on"
                class="ma-2"
                style="top: 8px; height: 56px"
                outlined
                dark>
                <v-icon>mdi-file-upload</v-icon
                <g-file-import id="file-chooser"></g-file-import>
            </v-btn>
            </template>
            <v-card>
                <v-card-title class="headline" color="primary" primary-title>Import Data</v-card-title>
                <v-card-text>
                Select a file with data you want to load into this instance of Jdaviz
                <v-container>
                    <v-row>
                    <v-col>
                        <g-file-import id="file-chooser"></g-file-import>
                        <span style="color: red;">{{ error_message }}</span>
                    </v-col>
                    </v-row>
                </v-container>
                </v-card-text>

                <v-card-actions>
                <div class="flex-grow-1"></div>
                    <v-btn color="primary" text @click="file_chooser_visible = false">Cancel</v-btn>
                    <v-btn color="primary" text @click="choose_file" :disabled="!valid_path">Import</v-btn>
                </v-card-actions>

            </v-card>
         </v-dialog>
    </v-row>

    <v-row>
      <v-btn
        v-for="config in configs"
        class="mx-2"
        color="primary"
        outlined=True
        style="height: 160px"
        @click="launch_config(config)"
        :disabled="!compatible_configs.includes(config)">
            <v-img
                max-height="100"
                max-width="100"
                :alt="config.charAt(0).toUpperCase() + config.slice(1)"
                :title="config.charAt(0).toUpperCase() + config.slice(1)"
                :style="!compatible_configs.includes(config) ? 'filter: opacity(25%) saturate(0)' : ''"
                :src="config_icons[config]"></v-img>
            <span style="position: absolute; bottom: -24px">
                {{ config }}
            </span>
      </v-btn>
    </v-row>
  </div>
</template>
