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


              <div style="display: grid"> <!-- overlay container -->
                    <div style="grid-area: 1/1">
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
                    </div>
                    <div v-if="format_items_spinner"
                        class="text-center"
                        style="grid-area: 1/1;
                                z-index:2;
                                margin-left: -24px;
                                margin-right: -24px;
                                padding-top: 24px;
                                background-color: rgb(0 0 0 / 20%)">
                        <v-progress-circular
                            indeterminate
                            color="spinner"
                            size="50"
                            width="6"
                        />
                    </div>
                </div> <!-- overlay container -->
        </v-card-text>
    </v-card>
</template>
  