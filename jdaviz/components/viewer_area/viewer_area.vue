<template>
  <splitpanes class="fill-height" horizontal>
    <pane v-for="(row, i) in viewers">
      <splitpanes>
        <pane v-for="(col, j) in row">
          <v-tabs v-model="col.tab" height="36px" class="fill-height">
            <draggable
                    v-model="col.items"
                    :group="{name: 'viewers'}"
                    class="d-flex flex-grow-1"
            >
              <v-tab
                      v-for="item in col.items"
                      :key="item.id"
                      @click=""
              >
                {{ item.title }}
                <v-spacer></v-spacer>
                <v-btn icon x-small @click.stop="close_tab(item.id)" style="margin-left: 10px">
                  <v-icon>mdi-close</v-icon>
                </v-btn>
              </v-tab>
            </draggable>

            <v-tabs-items v-model="col.tab" class="fill-height">
              <v-tab-item v-for="item in col.items"
                          :key="item.id"
                          transition="false"
                          reverse-transition="false"
                          class="fill-height">
                <v-card flat style="height: calc(100% - 32px)">
                  <v-toolbar dense flat>
                    <v-toolbar-items>
                      <jupyter-widget :widget="item.tools" style="height: calc(100% - 48px);"/>
                    </v-toolbar-items>
                  </v-toolbar>
                  <jupyter-widget :widget="item.widget" />
                </v-card>

              </v-tab-item>
            </v-tabs-items>
          </v-tabs>
        </pane>
      </splitpanes>
    </pane>
  </splitpanes>
</template>
