<template>
  <v-tabs
    v-model="tab"
    height="36px"
    background-color="blue lighten-5"
    style="height: calc(100% - 36px)"
  >
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
        <v-toolbar dense flat>
          <jupyter-widget :widget="item.tools" />
          <v-divider vertical></v-divider>
          <v-toolbar-items>
            <v-select solo flat :items="dc_items" @change="data_selected" label="Data"></v-select>
          </v-toolbar-items>
          <v-spacer></v-spacer>
          <v-divider vertical></v-divider>
          <v-toolbar-items>
            <v-menu offset-y :close-on-content-click="false" left>
              <template v-slot:activator="{ on }">
                <v-btn v-on="on" icon>
                  <v-icon>mdi-settings</v-icon>
                </v-btn>
              </template>
              <v-tabs grow height="36px" style="height: 100%">
                <v-tab>Data</v-tab>
                <v-tab>Layer</v-tab>
                <v-tab>Viewer</v-tab>

                <v-tab-item class="overflow-y-auto" style="height: 100%">
                  <v-treeview
                    dense
                    selectable
                    :items="data_items"
                    v-model="selected_data_items"
                    hoverable
                    activatable
                  ></v-treeview>
                </v-tab-item>
                <v-tab-item>
                  <v-card flat class="overflow-y-auto" style="height: 100%">
                    <jupyter-widget :widget="item.layer_options" />
                  </v-card>
                </v-tab-item>
                <v-tab-item>
                  <v-card flat class="overflow-y-auto" style="height: 100%">
                    <jupyter-widget :widget="item.viewer_options" />
                  </v-card>
                </v-tab-item>
              </v-tabs>
            </v-menu>
          </v-toolbar-items>
        </v-toolbar>

        <v-divider></v-divider>

        <jupyter-widget :widget="item.widget" style="width: 100%; height: 100%" />
      </v-tab-item>
    </v-tabs-items>
  </v-tabs>
</template>