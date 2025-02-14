<template>
    <v-card>
        <v-card-title class="headline" color="primary" primary-title>Download from URL</v-card-title>

        <v-card-text>
            <v-text-field
                v-model='url'
                prepend-icon='mdi-link-box'
                style="padding: 0px 8px"
                hide-details
            ></v-text-field>

            <plugin-switch
                :value.sync="cache"
                label="Cache File"
                api_hint="loader.cache = "
                :api_hints_enabled="false"
                hint="Whether to attempt to read from the cache if this same URL has been previously fetched."
              />


              <plugin-select
                    :show_if_single_entry="true"
                    :items="format_items.map(i => i.label)"
                    :selected.sync="format_selected"
                    label="Format"
                    api_hint="loader.format ="
                    :api_hints_enabled="false"
                    hint="Choose input format"
                />
                <div v-if="format_selected.length">
                    <p>Importer Options:</p>
                    <jupyter-widget :widget="importer_widget"></jupyter-widget>
                </div>
        </v-card-text>
    </v-card>
</template>
  