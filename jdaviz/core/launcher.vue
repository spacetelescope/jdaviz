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
        label="File Path"
        :hint="hint"
        persistent-hint
        >
        </v-text-field>
        <v-progress-circular
            v-if="hint === 'Please wait. Identifying file...'"
            indeterminate
            color="spinner"
            size="45"
            width="4"
        ></v-progress-circular>
    </v-row>

    <v-row>
      <v-btn
        v-for="config in configs"
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
              :src="config_icons[config]"></v-img>
          <span style="position: absolute; bottom: -24px">
              {{ config }}
          </span>
      </v-btn>
    </v-row>
  </div>
</template>
