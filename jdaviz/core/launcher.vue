<template>
  <div>
    <h1>Welcome to jdaviz!</h1>
    
    <v-row>
      <v-text-field
        v-model="filepath"
        label="File Path"
        :hint="hint"
        persistent-hint
      >
      </v-text-field>
    </v-row>
    
    <v-row>
      <v-btn
        prepend-icon="mdi-check-circle"
        class="ma-2"
        color="primary"
        outlined=True
        v-for="config in configs"
        @click="launch_config(config)"
        :disabled="!compatible_configs.includes(config)">
        <img
            :alt="config.charAt(0).toUpperCase() + config.slice(1)"
            :title="config.charAt(0).toUpperCase() + config.slice(1)"
            width="100px"
            :src="config_icons[config]">
      </v-btn>
    </v-row>
  </div>
</template>