<template>
  <div class="mx-12">
    <span style="float: right; font-weight: 100; color: white">
        <a :href="'https://jdaviz.readthedocs.io/en/'+vdocs" target="__blank" style="color: white">
            <b>Learn More</b>
        </a>
        |
        <a :href="'https://spacetelescope.github.io/jdat_notebooks/'" target="__blank" style="color: white">
            <b>Notebooks</b>
        </a>
        |
        <a :href="'https://github.com/spacetelescope/jdaviz'" target="__blank" style="color: white">
            <b>GitHub</b>
        </a>
    </span>

    <h1 class="mt-8 mb-6" style="color: white">Welcome to Jdaviz!</h1>
    
    <v-row>
        <v-text-field
            v-model="filepath"
            class="my-4"
            autofocus="true"
            dark
            outlined
            label="File Path"
            :hint="hint"
            persistent-hint
            :loading="hint === 'Identifying which tool is best to visualize your file...' ? '#C75109' : 'false' " 
        >
        </v-text-field>

        <j-tooltip tooltipcontent="select file from disk" span_style="height: 80px">
          <v-dialog v-model="file_browser_visible" max-width="1000" max-height="800">
              <template v-slot:activator="{ on }">
                  <v-btn
                      v-on="on"
                      @click="open_file_dialog"
                      class="ma-2"
                      color="#1E617F"
                      style="top: 7px; height: 57px"
                      dark>
                      <v-icon large>mdi-file-upload</v-icon>
                  </v-btn>
              </template>
              <v-card max-height="800">
                  <v-card-title class="headline" color="primary" primary-title>Select Data</v-card-title>
                  <v-card-text style="max-height: 650px; overflow-y: auto;">
                  Select a file with data you want to load into this instance of Jdaviz. Jdaviz will
                  attempt to identify a compatible configuration for your selected dataset. If one cannot
                  be found, you can manually select a configuration to load your data into.
                  <v-container>
                      <v-row>
                      <v-col>
                          <jupyter-widget :widget="file_browser_widget" v-if="file_browser_widget"/>
                      </v-col>
                      </v-row>
                  </v-container>
                  </v-card-text>

                  <v-card-actions>
                  <div class="flex-grow-1"></div>
                      <v-btn color="primary" text @click="file_browser_visible = false">Cancel</v-btn>
                      <v-btn color="primary" text @click="choose_file">Import</v-btn>
                  </v-card-actions>

              </v-card>
           </v-dialog>
        </j-tooltip>
    </v-row>

    <v-row justify="center">
      <v-btn
        v-for="config in configs"
        class="mx-3"
        color="#FFFFFF"
        style="height: 180px; width: 115px"
        @click="launch_config({config: config})"
        :disabled="!compatible_configs.includes(config)">
            <div class="item" align="center">
                <v-img
                    height="100"
                    width="100"
                    :alt="config.charAt(0).toUpperCase() + config.slice(1)"
                    :title="config.charAt(0).toUpperCase() + config.slice(1)"
                    :style="!compatible_configs.includes(config) ? 'filter: opacity(25%) saturate(0)' : ''"
                    :src="config_icons[config]"></v-img>
                
                <span class="bold" :style="compatible_configs.includes(config) ? 'font-size: 1.3em; color: #013B4D'
                                                                            : 'font-size: 1.3em; color: #013B4D75'">
                    <br>
                    {{ config }}
                </span>
            </div>
      </v-btn>
    </v-row>
  </div>
</template>
