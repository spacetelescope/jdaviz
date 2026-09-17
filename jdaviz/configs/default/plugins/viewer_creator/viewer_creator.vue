<template>
  <v-menu location="bottom">
    <template v-slot:activator="{ props }">
      <!-- <v-tooltip> -->
        <!-- <template v-slot:activator="{ props }"> -->
          <v-btn icon rounded="0" v-bind="props">
            <v-icon>mdi-chart-histogram</v-icon>
          </v-btn>
        <!-- </template> -->
        <!-- <span>Viewers</span> -->
      <!-- </v-tooltip> -->
    </template>
    <v-list>
      <v-list-item v-for="(viewer, i) in viewer_types" @click="create_viewer(viewer.name)">
        <div class="v-list-item-content">{{ viewer.label }}</div>
      </v-list-item>
    </v-list>
  </v-menu>
</template>
