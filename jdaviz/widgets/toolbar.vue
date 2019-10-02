<template>
    <v-app-bar
            app
            color="indigo"
            dark
    >
        <v-app-bar-nav-icon v-on:click.stop="$emit('show-drawer')"></v-app-bar-nav-icon>
        <v-toolbar-title>Application</v-toolbar-title>
        <component v-for="name in tool_names" v-bind:is="name"></component>
    </v-app-bar>
</template>
