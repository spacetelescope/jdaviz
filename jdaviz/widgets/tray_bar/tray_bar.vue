<template>
  <v-navigation-drawer
          v-model="drawer"
          clipped
          app
          :mini-variant.sync="mini"
          width=320
          mini-variant-width=49
          stateless
          class="fill-height"
          :absolute="checkNotebookContext()"
  >
    <golden-layout style="height: 100%"
      :showPopoutIcon="false"
    >
      <gl-row>
        <gl-col>
          <gl-stack>
            <gl-component v-for="item in tray_items"
                          :key="item.name"
                          :title="item.label"
                          :closable="false"
            >
              <component v-bind:is="item.name"></component>
            </gl-component>
          </gl-stack>
          <gl-stack>
            <gl-component :key="item.name"
                          v-for="item in tray_items"
                          :title="item.label"
            >
              <component v-bind:is="item.name"></component>
            </gl-component>
          </gl-stack>
        </gl-col>
      </gl-row>
    </golden-layout>

    <!-- <v-tabs v-model="tab" @change="tab_changed" vertical optional>
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
              style="overflow: auto"
              v-for="item in tray_items"
              :key="item.name"
      >
            <!-- <v-card flat> -->
          <!-- <component v-bind:is="item.name"></component> -->
<!--              <g-data-collection-list></g-data-collection-list>-->
<!--              <g-test></g-test>-->
            <!-- </v-card> -->
      <!-- </v-tab-item>
    </v-tabs> -->
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
    </v-card>  -->
  </v-navigation-drawer>
</template>
