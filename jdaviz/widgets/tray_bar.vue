<template>
  <v-navigation-drawer
          v-model="drawer"
          clipped
          width="360px"
          app
  >
    <v-card
            flat
            tile
            height="100%"
    >
      <v-tabs
              vertical
              background-color="accent"
              class="fill-height"
              v-model="tab"
      >
        <template v-for="item in tray_items">
          <v-tooltip right>
            <template v-slot:activator="{ on }">
              <v-tab :key="item.name"
                     style="min-width: 50px"
                     v-on="on"
              >
                <v-icon>{{ item.icon }}</v-icon>
              </v-tab>
            </template>
            <span>{{ item.label }}</span>
          </v-tooltip>
        </template>

        <v-tabs-items
                v-model="tab">
          <v-tab-item
                  v-for="item in tray_items"
                  :key="item.name"
          >
            <v-card flat>
              <component v-bind:is="item.name"></component>
<!--              <g-data-collection-list></g-data-collection-list>-->
<!--              <g-test></g-test>-->
            </v-card>
          </v-tab-item>
        </v-tabs-items>
      </v-tabs>
    </v-card>
  </v-navigation-drawer>
</template>
