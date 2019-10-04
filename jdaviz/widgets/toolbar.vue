<template>
  <v-app-bar
          app
          color="indigo"
          dark
          dense
          clipped-left
  >
    <!--        <v-toolbar-items >-->
    <template v-for="name in tool_names">
      <component v-bind:is="name"></component>
    </template>
    <!--        </v-toolbar-items>-->
  </v-app-bar>
</template>
