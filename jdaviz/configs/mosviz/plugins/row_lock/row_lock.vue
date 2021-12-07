<template>
  <j-tooltip tipid="lock-row-toggle">
    <v-btn 
      icon
      @click="toggle_lock"
      :class="{active: is_locked}">
      <v-icon>mdi-vector-link</v-icon>
    </v-btn>
  </j-tooltip>
</template>
