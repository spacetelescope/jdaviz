<template>
    <v-card>
        <v-card-title class="headline" color="primary" primary-title>Download from URL</v-card-title>

        <v-card-text>
            <v-text-field
                v-model='url'
                prepend-icon='mdi-link-box'
                style="padding: 0px 8px"
                clearable
                hide-details
            ></v-text-field>
        </v-card-text>
    </v-card>
</template>
  