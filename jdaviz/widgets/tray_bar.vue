<template>
  <v-navigation-drawer
          v-model="drawer"
          clipped
          width="400px"
  >
    <v-card
            dark
            flat
            tile
            height="100%"
    >
      <v-tabs
              vertical
              icons-and-text
              background-color="indigo"
              class="fill-height"
              v-model="tab"
      >
        <v-tab
                v-for="item in tray_items"
                :key="item.name"
        >
          <v-icon>{{ item.icon }}</v-icon>
        </v-tab>

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
