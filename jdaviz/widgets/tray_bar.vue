<template>
  <v-navigation-drawer
          v-model="drawer"
          clipped
          :app="app"
          width="400px"
  >
    <v-card flat class="pa-2">
    <v-expansion-panels multiple>
      <v-expansion-panel
              v-for="(item, index) in tray_items"
              :key="index"
      >
        <v-expansion-panel-header>{{ item.label }}</v-expansion-panel-header>
        <v-expansion-panel-content>
          <component v-bind:is="item.name"></component>
        </v-expansion-panel-content>
      </v-expansion-panel>
    </v-expansion-panels>
    </v-card>
  </v-navigation-drawer>
</template>
