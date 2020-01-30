<template>
  <splitpanes class="fill-height" horizontal>
    <pane v-for="(row, i) in viewers">
      <splitpanes>
        <pane v-for="(col, j) in row">
          <v-tabs v-model="col.tab" height="36px" class="fill-height" background-color="blue lighten-5">
            <draggable v-model="col.items" :group="{name: 'viewers'}" class="d-flex flex-grow-1">
              <v-tab v-for="item in col.items" :key="item.id">
                {{ item.title }}
                <v-spacer></v-spacer>
                <v-btn icon x-small @click.stop="close_tab(item.id)" style="margin-left: 10px">
                  <v-icon>mdi-close</v-icon>
                </v-btn>
              </v-tab>
            </draggable>

            <v-tabs-items v-model="col.tab" class="fill-height">
              <v-tab-item
                v-for="item in col.items"
                :key="item.id"
                transition="false"
                reverse-transition="false"
                class="fill-height"
              >
                <v-sheet class="fill-height" style="position: relative;">
                  <v-toolbar dense flat>
                    <v-toolbar-items>
                      <jupyter-widget :widget="item.tools" />
                      <v-divider></v-divider>
                      <v-spacer></v-spacer>
                      <v-btn icon @click.stop="item.drawer = !item.drawer">
                        <v-icon>mdi-settings</v-icon>
                      </v-btn>
                    </v-toolbar-items>
                  </v-toolbar>

                  <v-divider></v-divider>

                  <v-navigation-drawer v-model="item.drawer" absolute temporary right overlay-opacity="0">
                    <v-tabs grow height="36px" >
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
        </pane>
      </splitpanes>
    </pane>
  </splitpanes>
</template>
