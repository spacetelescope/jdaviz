<template>
  <v-tabs v-model="tab" height="36px" class="fill-height" background-color="blue lighten-5">
    <draggable v-model="items" :group="{name: 'viewers'}" class="d-flex flex-grow-1">
      <v-tab v-for="item in items" :key="item.id">
        {{ item.title }}
        <v-spacer></v-spacer>
        <v-btn icon x-small @click.stop="close_tab(item.id)" style="margin-left: 10px">
          <v-icon>mdi-close</v-icon>
        </v-btn>
      </v-tab>
    </draggable>

    <v-btn icon tile @click.stop="split_pane('horizontal')">
      <v-icon>mdi-view-split-horizontal</v-icon>
    </v-btn>

    <v-btn icon tile @click.stop="split_pane('vertical')">
      <v-icon>mdi-view-split-vertical</v-icon>
    </v-btn>

    <v-tabs-items v-model="tab" class="fill-height">
      <v-tab-item
        v-for="item in items"
        :key="item.id"
        transition="false"
        reverse-transition="false"
        class="fill-height"
      >
        <v-sheet class="fill-height" style="position: relative;">
          <v-toolbar dense flat>
            <v-toolbar-items>
              <jupyter-widget :widget="item.tools" />
              <v-divider vertical></v-divider>
              <v-select
                fill-width
                solo
                flat
                :items="dc_items"
                @change="data_selected"
                label="Data"
                ></v-select>
              <v-spacer></v-spacer>
              <v-divider vertical></v-divider>
              <v-btn icon @click.stop="drawer = !drawer">
                <v-icon>mdi-settings</v-icon>
              </v-btn>
            </v-toolbar-items>
          </v-toolbar>

          <v-divider></v-divider>

          <v-navigation-drawer v-model="drawer" absolute temporary right overlay-opacity="0" width="325px">
            <v-tabs grow height="36px">
              <v-tab>Layer</v-tab>
              <v-tab>Viewer</v-tab>

              <v-tab-item>
                <v-card flat class="scroll-y" height="100%">
                  <jupyter-widget :widget="item.layer_options" />
                </v-card>
              </v-tab-item>
              <v-tab-item>
                <v-card flat class="scroll-y" height="100%">
                  <jupyter-widget :widget="item.viewer_options" />
                </v-card>
              </v-tab-item>
            </v-tabs>
          </v-navigation-drawer>

          <v-container class="fill-height">
            <v-row align="center" justify="center" class="fill-height">
              <v-col class="fill-height">
                <jupyter-widget :widget="item.widget" />
              </v-col>
            </v-row>
          </v-container>
        </v-sheet>
      </v-tab-item>
    </v-tabs-items>
  </v-tabs>
</template>