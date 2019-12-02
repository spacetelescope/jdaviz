<template>
  <v-app-bar
          color="primary"
          dark
          dense
          flat
          clipped-left
          :app="app"
  >
    <slot></slot>
    <!--        <v-toolbar-items >-->
    <template v-for="name in tool_names">
      <component v-bind:is="name"></component>
    </template>
    <!--        </v-toolbar-items>-->
  </v-app-bar>
</template>
