<template>
    <j-loader
        title="Download from URL"
        :format_items_spinner="format_items_spinner"
        :format_items="format_items"
        :format_selected.sync="format_selected"
        :importer_widget="importer_widget"
    >
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
    </j-loader>
</template>