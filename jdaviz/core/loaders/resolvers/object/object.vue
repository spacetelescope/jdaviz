<template>
    <j-loader
        title="Python Object"
        :popout_button="popout_button"
        :target_items="target_items"
        :target_selected.sync="target_selected"
        :format_items_spinner="format_items_spinner"
        :format_items="format_items"
        :format_selected.sync="format_selected"
        :importer_widget="importer_widget"
        :api_hints_enabled="api_hints_enabled"
        :server_is_remote="server_is_remote"
    >
        <v-alert type="info">
            Access the user API in a notebook cell to import a python object.
        </v-alert>
        <v-text-field
            v-model='object_repr'
            prepend-icon='mdi-language-python'
            style="padding: 0px 8px"
            :disabled="true"
            label="ldr.object ="
            class="api-hint"
        ></v-text-field>

    </j-loader>
</template>