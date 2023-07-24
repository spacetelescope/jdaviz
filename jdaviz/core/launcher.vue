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
        <v-img
            contain
            max-height="100"
            max-width="100"
            :alt="config.charAt(0).toUpperCase() + config.slice(1)"
            :title="config.charAt(0).toUpperCase() + config.slice(1)"
            :src="config_icons[config]"><v-img>        
        {{ config }}
      </v-btn>
    </v-row>
  </div>
</template>