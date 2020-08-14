<template>
  <component :is="stack.container">
    <g-viewer-tab
      v-for="(child, index) in stack.children"
      :stack="child"
      :key="index"
      :data-items="dataItems"
      @resize="$emit('resize')"
      @destroy="$emit('destroy', $event)"
      @data-item-selected="$emit('data-item-selected', $event)"
    ></g-viewer-tab>
    <gl-component
      v-for="(viewer, index) in stack.viewers"
      :key="index"
      title="Test"
      :tab-id="viewer.id"
      @resize="$emit('resize')"
      @destroy="$emit('destroy', viewer.id)"
    >
      <v-card tile flat style="height: calc(100% - 2px); margin-top: -2px;">
        <v-toolbar
          dense
          floating
          absolute
          right
          :collapse="viewer.collapse"
          elevation="1"
          :width="viewer.collapse ? '48px' : null"
        >
          <v-toolbar-items>
            <v-btn icon @click="viewer.collapse = !viewer.collapse">
              <v-icon v-if="viewer.collapse">mdi-hammer-screwdriver</v-icon>
              <v-icon v-else>mdi-close</v-icon>
            </v-btn>
            <!-- <v-divider vertical></v-divider> -->
            <jupyter-widget :widget="viewer.tools"></jupyter-widget>
            <v-menu offset-y :close-on-content-click="false" style="z-index: 10">
              <template v-slot:activator="{ on }">
                <v-btn icon color="primary" v-on="on">
                  <v-icon>mdi-settings</v-icon>
                </v-btn>
              </template>

              <v-tabs v-model="viewer.tab" grow height="36px">
                <v-tab key="0">Data</v-tab>
                <v-tab key="1">Layer</v-tab>
                <v-tab key="2">Viewer</v-tab>
              </v-tabs>

              <v-tabs-items v-model="viewer.tab" style="max-height: 500px; width: 350px;">
                <v-tab-item key="0" class="overflow-y-auto" style="height: 450px">
                  <v-treeview
                    dense
                    selectable
                    :items="dataItems"
                    hoverable
                    v-model="viewer.selected_data_items"
                    activatable
                    item-disabled="locked"
                    @input="$emit('data-item-selected', {'id': viewer.id, 'selected_items': $event})"
                  ></v-treeview>
                </v-tab-item>

                <v-tab-item key="1" eager class="overflow-y-auto" style="height: 100%">
                  <v-sheet class="px-4">
                    <jupyter-widget :widget="viewer.layer_options" />
                  </v-sheet>
                </v-tab-item>

                <v-tab-item key="2" eager class="overflow-y-auto" style="height: 100%">
                  <v-sheet class="px-4">
                    <jupyter-widget :widget="viewer.viewer_options" />
                  </v-sheet>
                </v-tab-item>
              </v-tabs-items>
            </v-menu>
          </v-toolbar-items>
        </v-toolbar>
        <jupyter-widget :widget="viewer.widget" style="width: 100%; height: 100%" />
      </v-card>
    </gl-component>
  </component>
</template>

<script>
module.exports = {
  name: "g-viewer-tab",
  props: ["stack", "dataItems"],
  created() {
    this.$parent.childMe = () => {
      return this.$children[0];
    };
  },
  methods: {
    computeChildrenPath() {
      return this.$parent.computeChildrenPath();
    }
  },
  computed: {
    parentMe() {
      return this.$parent;
    },
    childMe() {
      return this.$children[0];
    }
  }
};
</script>
