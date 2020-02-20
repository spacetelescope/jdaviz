<template>
  <v-sheet style="height: 100%">
    <v-toolbar tile dense flat color="blue lighten-4">
      <v-toolbar-items>
        <g-file-loader></g-file-loader>

        <v-menu offset-y>
          <template v-slot:activator="{ on: menu }">
            <v-tooltip bottom>
              <template v-slot:activator="{ on: tooltip }">
                <v-btn icon tile v-on="{...tooltip, ...menu}">
                  <v-icon>mdi-chart-histogram</v-icon>
                </v-btn>
              </template>
              <span>Viewers</span>
            </v-tooltip>
          </template>
          <v-list>
            <v-list-item v-for="(viewer, i) in viewers" @click="create_viewer(viewer.name)">
              <v-list-item-content>{{ viewer.label }}</v-list-item-content>
            </v-list-item>
          </v-list>
        </v-menu>
        <v-tooltip bottom>
          <template v-slot:activator="{ on }">
            <v-btn disabled v-on="on" icon tile>
              <v-icon>mdi-format-superscript</v-icon>
            </v-btn>
          </template>
          <span>Arithmetic Editor</span>
        </v-tooltip>
      </v-toolbar-items>
      <v-spacer></v-spacer>
      <v-toolbar-items>
        <v-tooltip bottom>
          <template v-slot:activator="{ on }">
            <v-btn disabled v-on="on" icon tile>
              <v-icon>mdi-export</v-icon>
            </v-btn>
          </template>
          <span>Export Data</span>
        </v-tooltip>

        <v-tooltip bottom>
          <template v-slot:activator="{ on }">
            <v-btn disabled v-on="on" icon tile>
              <v-icon>mdi-delete</v-icon>
            </v-btn>
          </template>
          <span>Delete Data</span>
        </v-tooltip>
      </v-toolbar-items>
    </v-toolbar>

    <splitpanes horizontal>
      <pane>
        <v-tabs
          v-model="base_items_tab"
          height="36px"
          background-color="blue lighten-5"
          style="height: calc(100% - 36px - 48px)"
        >
          <v-tab v-for="item in base_items" :key="item.id" @click>{{ item.title }}</v-tab>
          <v-tabs-items v-model="base_items_tab" style="height: 100%">
            <v-tab-item
              v-for="item in base_items"
              :key="item.id"
              style="height: 100%"
              class="overflow-y-auto"
            >
              <component v-bind:is="item.widget"></component>
            </v-tab-item>
          </v-tabs-items>
        </v-tabs>
      </pane>
      <pane v-if="plugin_items.length > 0">
        <v-tabs
          v-model="plugin_items_tab"
          height="36px"
          background-color="blue lighten-5"
          style="height: calc(100% - 36px - 48px)"
        >
          <v-tab v-for="item in plugin_items" :key="item.id" @click>{{ item.title }}</v-tab>

          <v-tabs-items v-model="plugin_items_tab" style="height: 100%">
            <v-tab-item
              v-for="item in plugin_items"
              :key="item.id"
              style="height: 100%"
              class="overflow-y-auto"
            >
              <component v-bind:is="item.widget"></component>
            </v-tab-item>
          </v-tabs-items>
        </v-tabs>
      </pane>
    </splitpanes>
  </v-sheet>
</template>
