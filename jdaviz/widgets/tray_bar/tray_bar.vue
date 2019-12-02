<template>
  <v-navigation-drawer
          v-model="drawer"
          clipped
          :app="app"
          :mini-variant.sync="mini"
          width=300
          mini-variant-width=49
          stateless
  >
    <v-tabs v-model="tab" @change="tab_changed" vertical optional>
      <template v-for="item in tray_items">
        <v-tooltip right :key="item.name">
          <template v-slot:activator="{ on }">
            <v-tab :key="item.name"
                    style="width: 49px"
                    v-on="on"
            >
              <v-icon>{{ item.icon }}</v-icon>
            </v-tab>
          </template>
          <span>{{ item.label }}</span>
        </v-tooltip>
      </template>

      <v-tab-item
        v-for="item in tray_items"
        :key="item.name">
            <!-- <v-card flat> -->
          <component v-bind:is="item.name"></component>
<!--              <g-data-collection-list></g-data-collection-list>-->
<!--              <g-test></g-test>-->
            <!-- </v-card> -->
      </v-tab-item>
    </v-tabs>
    <!-- <v-card flat class="pa-2">
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
  </v-navigation-drawer> -->
</template>
