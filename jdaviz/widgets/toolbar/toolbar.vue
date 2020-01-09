<template>
  <v-app-bar
          color="primary"
          dark
          dense
          flat
          clipped-left
          app
          :absolute="checkNotebookContext()"
  >
    <slot></slot>
    <template v-for="name in tool_names">
      <component v-bind:is="name"></component>
    </template>
  </v-app-bar>
</template>
