<template>
    <v-app-bar
            app
            color="indigo"
            dark
            dense
    >

<!--        <v-toolbar-items>-->
            <component v-for="name in tool_names" v-bind:is="name"></component>
<!--        </v-toolbar-items>-->
    </v-app-bar>
</template>
