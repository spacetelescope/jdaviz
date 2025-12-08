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
    
    <!-- Data Import Buttons -->
    <v-row justify="center" class="my-6">
      <v-btn
        v-for="item in resolver_items"
        :key="item.name"
        class="mx-2"
        color="#1E617F"
        large
        dark
        @click="open_resolver_dialog(item.name)">
        <v-icon left>{{ get_resolver_icon(item.name) }}</v-icon>
        {{ item.label }}
      </v-btn>
    </v-row>

    <!-- Status/Hint Message -->
    <v-row justify="center" class="my-4" v-if="hint">
      <v-col cols="12" class="text-center">
        <div :style="hint ? 'color: #C75109; font-weight: bold; font-size: 1.1em;' : ''">
          {{ hint }}
        </div>
      </v-col>
    </v-row>

    <!-- Resolver Dialog Overlay -->
    <v-dialog v-model="resolver_dialog_visible" max-width="900" persistent>
      <v-card dark>
        <v-card-title class="headline" style="background-color: #1E617F; color: white;">
          <v-icon left color="white">{{ get_resolver_icon(active_resolver_tab) }}</v-icon>
          {{ get_resolver_title(active_resolver_tab) }}
          <v-spacer></v-spacer>
          <v-btn icon @click="close_resolver_dialog">
            <v-icon>mdi-close</v-icon>
          </v-btn>
        </v-card-title>
        <v-card-text class="pa-6" style="min-height: 400px; max-height: 600px; overflow-y: auto;">
          <jupyter-widget v-if="resolver_dialog_visible && active_resolver_widget" :widget="active_resolver_widget"></jupyter-widget>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn color="grey" text @click="close_resolver_dialog">Cancel</v-btn>
          <v-btn color="primary" @click="identify_data({resolver: active_resolver_tab})">
            Load Data
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

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

<script>
module.exports = {
  methods: {
    get_resolver_icon(resolver_name) {
      const icons = {
        'file': 'mdi-file-document',
        'file drop': 'mdi-file-upload',
        'url': 'mdi-web',
        'virtual observatory': 'mdi-telescope'
      };
      return icons[resolver_name] || 'mdi-help';
    },
    get_resolver_title(resolver_name) {
      const titles = {
        'file': 'Load from File',
        'file drop': 'Drop File',
        'url': 'Load from URL',
        'virtual observatory': 'Virtual Observatory'
      };
      return titles[resolver_name] || resolver_name;
    },
    open_resolver_dialog(resolver_name) {
      this.active_resolver_tab = resolver_name;
      this.resolver_dialog_visible = true;
    },
    close_resolver_dialog() {
      this.resolver_dialog_visible = false;
    }
  }
};
</script>
